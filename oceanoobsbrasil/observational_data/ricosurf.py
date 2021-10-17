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


class RicoSurf():

    def __init__(self,
        equip='visual'):

        self.db = GetData()
        self.equip = equip
        self.url = 'https://ricosurf.com.br/boletim-das-ondas/rio-janeiro'
        self.stations = self.db.get(table='stations', institution=['=', 'ricosurf'], data_type=['=', self.equip])

    def get(self):

        response = requests.get(self.url)

        soup = BeautifulSoup(response.text,'html.parser')

        self.beaches = self.beaches_with_data(soup)

        for index, station in self.stations.iterrows():
            print(station['name'])
            if self.beach_has_data(station):
                print('Data available')
                response = requests.get(station["url"])

                soup = BeautifulSoup(response.text,'html.parser')

                l = soup.find("div", {"class": "h5 text-primary margin-xxs-bottom"}).get_text(strip=True).replace(",", ".")
                swvht = float(l[0:-1])

                l = soup.find_all('div', attrs={'class': 'h5 no-margin text-primary'})
                tp = l[0].get_text(strip=True).replace(",", ".")
                tp = float(tp[0:-1])
                sst = l[1].get_text(strip=True)
                sst = float(sst[0:-2])
                wvdir = soup.find("div", {"class": "small line-height-xs"}).get_text(strip=True)
                date_time = datetime.date(datetime.now())

                values = np.array([date_time, swvht, tp, sst, wvdir])
                columns = ['date_time', 'swvht', 'tp', 'sst', 'wvdir']

                self.result = pd.DataFrame(values).T
                self.result.columns = columns
                self.result = self.result.replace(to_replace =['None', 'NULL', ' ', ''], value =np.nan)

                self.result['station_id'] = str(station['id'])
                self.db.feed_bd(table='data_stations', df=self.result)
                print('dados alimentados')
            else:
                print('No data for this station')


    def beach_has_data(self, station):
        if station['name'] in self.beaches:
            return True
        return False

    def beaches_with_data(self, soup):
        l = soup.find_all('a', attrs={'class': 'beach-peak col-xxs-12 col-xs-6 col-md-4'})
        beaches = []
        for beach in l:
            l1= beach.find('div', attrs={'class': 'place'}).get_text(strip=True)
            beaches.append(l1)
        return beaches

if __name__ == '__main__':
    RicoSurf().get()
