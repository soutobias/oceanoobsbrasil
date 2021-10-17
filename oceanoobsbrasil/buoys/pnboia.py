"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import time
import datetime
import urllib.request, json

import numpy as np

import pandas as pd
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData

from dotenv import load_dotenv
import os
import requests

class Pnboia():

    load_dotenv()

    def __init__(self, equip='buoy',
        start_date=(datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
        end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')):


        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(table='stations', institution=['=', 'pnboia'], data_type=['=', self.equip])

    def get(self, save_bd=False):
        for index, station in self.stations.iterrows():
            url=f"http://143.198.233.67/api/v1/data_buoys?buoy={station['url']}&start_date={self.start_date}&end_date={self.end_date}&token={os.getenv('REMOBS_TOKEN')}"

            response = requests.get(url).json()
            df = pd.DataFrame(response)
            for i in df.columns:
                try:
                    df[i] = pd.to_numeric(df[i])
                except:
                    pass
            df['date_time'] = pd.to_datetime(df['date_time'], format='%Y-%m-%dT%H:%M:%S.000Z')
            df.sort_values('date_time', inplace=True)

            df = df[['date_time', 'lat', 'lon', 'rh', 'pres', 'atmp',
                   'dewpt', 'wspd', 'wdir',
                   'gust', 'arad', 'sst',
                   'swvht1', 'mxwvht1', 'tp1','wvdir1']]

            df.columns = ['date_time', 'lat', 'lon', 'rh', 'pres', 'atmp',
                   'dewpt', 'wspd', 'wdir',
                   'gust', 'arad', 'sst',
                   'swvht', 'mxwvht', 'tp','wvdir']

            self.result = df.copy()

            if len(self.result) == 0:
                print ("Nao ha dados para essa boia")
            else:
                self.result = self.result.replace(to_replace =['None', 'NULL', ' ', ''],
                                        value =np.nan)
                if save_bd:
                    self.result['station_id'] = str(station['id'])
                    self.db.feed_bd(table='data_stations', df=self.result)
                else:
                    return self.result

if __name__ == '__main__':
    Pnboia().get(save_bd=True)
