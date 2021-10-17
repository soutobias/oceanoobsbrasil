"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup


class ESBuoy():

    load_dotenv()

    def __init__(self, equip='buoy'):

        self.bd = GetData()
        self.url=os.getenv('ES_URL')

        self.equip = equip
        self.stations = self.bd.get(table='stations', institution=['=', 'codesa'], data_type=['=', self.equip]).iloc[0]

    def get(self):

        resp = requests.get(self.url)

        self.soup = BeautifulSoup(resp.text,'html.parser')

        try:
            date_time = self.soup.find("h4", {"class": "titulo"}).text
            date_time = datetime.strptime(date_time, '%d/%m/%Y %H:%M:%S')
        except:
            print('problem with the website')
            return

        wdir = self.get_data('data-wind-direction-deg')
        wspd = self.get_data('data-wind-speed-knot')
        atmp = self.get_data('data-air-temperature')
        swvht = self.get_data('data-height-wave')
        wvdir = self.get_data('data-wave-direction')
        tp = self.get_data('data-peak-wave-period')
        pres = self.get_data('data-atmosferic-pressure')
        rh = self.get_data('data-relative-humidity')


        values = np.array([date_time, wdir, wspd, atmp, swvht, wvdir, tp, pres, rh])
        columns = ['date_time','wdir','wspd','atmp','swvht','wvdir','tp','pres','rh']
        self.result = pd.DataFrame(values).T
        self.result.columns = columns

        self.result.date_time = self.result.date_time + timedelta(hours=3)


        self.result['station_id'] = str(self.stations['id'])
        self.db.feed_bd(table='data_stations', df=self.result)

    def get_data(self, attrs):
        try:
            value = float(self.soup.find("h3", {attrs: True})[attrs])
        except:
            value = np.nan
        return value


if __name__ == '__main__':
    ESBuoy().get()
