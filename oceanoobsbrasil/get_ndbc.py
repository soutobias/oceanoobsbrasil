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
import re
from oceanoobsbrasil.bd import GetData


class Ndbc():

    def __init__(self, lat=[-35.8333, 7],
        lon=[-55.20, 20],
        hours=12):

        self.db = GetData()
        self.lat = lat
        self.lon = lon
        self.hours = hours

        self.start_date = datetime.utcnow()-timedelta(hours=self.hours)
        self.end_date = datetime.utcnow()

        self.url=f"https://www.ndbc.noaa.gov/box_search.php?lat1={lat[0]}&lat2={lat[1]}&lon1={lon[0]}&lon2={lon[1]}&uom=M&ot=A&time={hours}"

    def get(self, save_bd=False):

        resp = requests.get(self.url)

        soup = BeautifulSoup(resp.text,'html.parser')

        lines = soup.find_all('span', attrs={'style': 'background-color: #f0f8fe'})
        values=[]

        for line in lines:
            line = line.get_text(strip=True)
            line = line.replace("B", " B")
            line = re.sub(" +", ",", line).split(",")
            values.append(line)

        lines = soup.find_all('span', attrs={'style': 'background-color: #fffff0'})
        for line in lines:
            line = line.get_text(strip=True)
            line = line.replace("B", " B")
            line = re.sub(" +", ",", line).split(",")
            values.append(line)

        columns=['ID','T1','hour','LAT','LON','WDIR','WSPD','GST','WVHT','DPD','APD','MWD','PRES','PTDY','ATMP','WTMP','DEWP','VIS','TCC','TIDE','S1HT','S1PD','S1DIR','S2HT','S2PD','S2DIR']

        df = pd.DataFrame(values).iloc[: , :26]
        df.columns = columns
        df.replace('-', np.nan, inplace=True)

        df.hour = (df.hour.astype(int)/100).astype(int)
        df['date_time'] = df['hour'].apply(lambda x: self.calculate_date(x))

        self.result = df[['date_time','LAT','LON','WDIR','WSPD','WVHT','DPD','MWD','PRES','ATMP','WTMP','DEWP','S1HT','S1DIR']].copy()
        self.result.columns = ['date_time', 'lat', 'lon', 'wdir', 'wspd', 'swvht', 'tp', 'wvdir', 'pres', 'atmp', 'sst', 'dewpt', 'swvht_swell', 'wvdir_swell']

        self.convert_to_numeric()

        if save_bd:
            self.result["institution"] = 'ndbc'
            self.result["data_type"] = 'gts'

            self.feed_bd()
        else:
            return self.result

    def feed_bd(self):

        self.db.post(table='data_no_stations', df=self.result, data_type='gts')

    def calculate_date(self, x):
        start_date = datetime.utcnow()-timedelta(hours=12)
        end_date = datetime.utcnow()
        if x >= end_date.hour + 2:
            value = start_date
            value = value.replace(hour=x)
        else:
            value = end_date
            value = value.replace(hour=x)

        value = value.replace(minute=0)
        value = value.replace(second=0)
        value = value.replace(microsecond=0)
        return value

    def convert_to_numeric(self):
        columns = self.result.drop(columns='date_time').columns
        for column in columns:
            self.result[column] = pd.to_numeric(self.result[column], errors='coerce')

