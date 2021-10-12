"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import time
import datetime
import urllib.request, json
import requests

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from oceanoobsbrasil.db import GetData


class Wave():

    def __init__(self,
        equip='visual'):

        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(table='stations', institution=['=', 'wavecheck'], data_type=['=', self.equip])

    def get(self):
        for index, station in self.stations.iterrows():
            response = requests.get(station["url"])

            soup = BeautifulSoup(response.text,'html.parser')
            no_data = soup.find("p", {"class": "alerta-pico-desatualizado"})
            print(station['name'])
            if not no_data:
                print("Tem dados para esse pico")

                l = soup.find("td", {"id": "forecast_wave_size"}).get_text(strip=True)
                try:
                    [k1,k2]=l.split("m")
                    swvht = float(k1)
                except:
                    swvht = 0

                l = soup.find("td", {"id": "forecast_wave_direction"}).get_text(strip=True)
                wvdir = str(l)

                date_time = datetime.date(datetime.now())

                values = np.array([date_time, swvht, wvdir])
                columns = ['date_time', 'swvht', 'wvdir']

                self.result = pd.DataFrame(values).T
                self.result.columns = columns
                self.result['station_id'] = str(station['id'])
                self.db.feed_bd(table='data_stations', df=self.result)
                print('dados alimentados')
            else:
                print('No data for this station')
