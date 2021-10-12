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


class CleanBeach():

    def __init__(self,
        equip='cleaning'):

        self.db = GetData()
        self.equip = equip
        self.url = 'https://praialimpa.net/'
        self.stations = self.db.get(table='stations', institution=['=', 'inea'], data_type=['=', self.equip])

    def get(self):
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text,'html.parser')
        beaches = soup.find_all("div", {"class": "beach"})
        for beach in beaches:
            name = beach.find("div", {"class": "name"}).text
            location = beach.find("div", {"class": "location"}).text
            station = self.stations[(self.stations.url==location) & (self.stations.name==name)]
            print(name, location)
            if not station.empty:
                if beach.find("div", {"class": "status propria"}):
                    cleaning = True
                else:
                    cleaning = False
                date_time = datetime.date(datetime.now())

                values = np.array([date_time, cleaning])
                columns = ['date_time', 'cleaning']

                self.result = pd.DataFrame(values).T
                self.result.columns = columns
                self.result['station_id'] = str(station['id'].iloc[0])
                self.feed_bd()
                print('dados alimentados')
            else:
                print('No data for this station')

    def feed_bd(self):
        self.db.post(table='data_stations', df=self.result)

