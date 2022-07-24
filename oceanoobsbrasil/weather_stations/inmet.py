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
import warnings
warnings.filterwarnings("ignore")


class Inmet():

    def __init__(self,
        start_date=(datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d'),
        end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d'),
        api="https://apitempo.inmet.gov.br"):

        self.db = GetData()
        self.api = api
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(table='stations', institution=['=', 'inmet'])

    def get(self,
        save_bd=True):

        for index, station in self.stations.iterrows():
            print(station.url)

            url = f"{self.api}/estacao/{self.start_date}/{self.end_date}/{station.url}"

            response = requests.get(url,headers={'referer': 'https://www.google.com/'})
            df = pd.DataFrame(response)

            if response.status_code == 200:
                df = pd.DataFrame(response.json())
                df = df[['PRE_INS', 'VEN_DIR', 'DT_MEDICAO', 'VEN_VEL','VEN_RAJ', 'TEM_INS',
                         'HR_MEDICAO']]
                df.columns = ['pres', 'wdir', 'date', 'wspd', 'gust', 'atmp', 'hour']
                df['date_time'] = pd.to_datetime(df['date'] + df['hour'], format='%Y-%m-%d%H%M')
                df.drop(columns=['date', 'hour'], inplace=True)
                df = df[df.date_time <datetime.utcnow()]

                self.result = df.replace(to_replace =['None', 'NULL', ' ', ''],
                                        value =np.nan)

                self.result.date_time = self.result.date_time + timedelta(hours=3)

                self.result['gust'] = pd.to_numeric(self.result['gust'], errors='coerce')
                self.result.gust[self.result.gust.notnull()] = (self.result.gust[self.result.gust.notnull()]*1.94384).round(decimals=1)
                self.result['wspd'] = pd.to_numeric(self.result['wspd'], errors='coerce')
                self.result.wspd[self.result.wspd.notnull()] = (self.result.wspd[self.result.wspd.notnull()]*1.94384).round(decimals=1)


                if save_bd:
                    self.result['station_id'] = str(station['id'])
                    self.db.feed_bd(table='data_stations', df=self.result)
                else:
                    return self.result
            else:
                print ("Nao ha dados para essa estação")

if __name__ == '__main__':
    Inmet().get(save_bd=True)
