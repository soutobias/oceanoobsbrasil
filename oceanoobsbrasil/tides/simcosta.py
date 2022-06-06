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

class SimcostaTide():

    def __init__(self, equip='tide',
        start_date=str(int(np.ceil(time.time()-3600*100))),
        end_date=str(int(np.ceil(time.time())))):
        # Connect to the database

        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(table='stations', institution=['=', 'simcosta'], data_type=['=', self.equip])

    def get(self):
        for index, station in self.stations.iterrows():
            url_address = f"https://simcosta.furg.br/api/intrans_data?boiaID={station['url']}&type=json&time1={self.start_date}&time2={self.end_date}&params=water_l1"
            with urllib.request.urlopen(url_address) as url:
                data = json.loads(url.read().decode())
                self.data = pd.DataFrame(data)
            url_address = f"https://simcosta.furg.br/api/intrans_data?boiaID={station['url']}&type=json&time1={self.start_date}&time2={self.end_date}&params=relative_humidity,wind_direction,wind_speed,dew_point,atm_pressure,air_temp"
            with urllib.request.urlopen(url_address) as url:
                data1 = json.loads(url.read().decode())
                self.data1 = pd.DataFrame(data1)
            self.result = pd.concat([self.data,  self.data1], axis=1, join='inner')

            self.remove_dup_columns()

            if len(self.result) == 0:
                print ("Nao ha dados para essa boia")
            else:
                self.result['date_time'] = pd.to_datetime(self.result.timestamp)
                self.result = self.result[['water_l1', 'wind_speed', 'wind_direction', 'air_temp',
                    'relative_humidity', 'atm_pressure', 'date_time']]
                self.result.columns = ['water_level', 'wspd', 'wdir', 'atmp', 'rh', 'pres', 'date_time']

                self.result = self.result.replace(to_replace =['None', 'NULL', ' ', ''],
                                        value =np.nan)
                self.result['station_id'] = str(station['id'])
                self.db.feed_bd(table='data_stations', df=self.result)

    def remove_dup_columns(self):
        keep_names = set()
        keep_icols = list()
        for icol, name in enumerate(self.result.columns):
            if name not in keep_names:
                keep_names.add(name)
                keep_icols.append(icol)
        self.result = self.result.iloc[:, keep_icols]

if __name__ == '__main__':
    SimcostaTide().get()
