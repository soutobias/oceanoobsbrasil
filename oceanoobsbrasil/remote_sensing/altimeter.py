
import pandas as pd
import numpy as np

from datetime import datetime, timedelta
import time

from oceanoobsbrasil.db import GetData

import glob, os

import re
import urllib.request
import requests
from netCDF4 import Dataset
from bs4 import BeautifulSoup

from os.path import expanduser


class Altimeter():


    def __init__(self,
        start_date=datetime.utcnow()-timedelta(days=1),
        end_date=datetime.utcnow(),
        directory='jason3/ogdr/ogdr/',
        url='https://www.ncei.noaa.gov/data/oceans/',
        lat=[-36, 8],
        lon=[-50, -20]):


        self.directory = directory
        self.start_date = start_date
        self.end_date = end_date
        self.url = url

        self.db = GetData()
        self.lat = lat
        self.lon = lon

        home = expanduser("~")
        self.path = f"{home}/data"


    def get(self):

        time_2000_1970 = (datetime(2000,1,1) - datetime(1970,1,1)).total_seconds()
        self.get_nc_files()

        for f in  self.nc_files:
            print(f)
            NC = Dataset(f,'r')
            tempo = NC.groups['data_01'].variables['time']
            lat = NC.groups['data_01'].variables['latitude']
            lon = NC.groups['data_01'].variables['longitude']
            wspd = NC.groups['data_01'].variables['wind_speed_alt']
            swvht = NC.groups['data_01'].groups["ku"].variables['swh_ocean']
            flag = NC.groups['data_01'].groups["ku"].variables['swh_ocean_compression_qual']

            ar = np.array([tempo, lat, lon, wspd, swvht, flag])
            df = pd.DataFrame(ar).T

            columns = ['date_time', 'lat', 'lon', 'wspd', 'swvht', 'flag']
            df.columns = columns

            df.lon = df.lon - 180
            df.date_time = df.date_time + time_2000_1970
            df.date_time = pd.to_datetime(df['date_time'],unit='s')
            df = df[(df.lat > self.lat[0]) & (df.lat < self.lat[1]) & (df.lon < self.lon[1]) & (df.lon > self.lon[0])]
            self.result = df[(df.wspd < 9999) & (df.swvht < 9999)]
            if not self.result.empty:
                print('data for brazilian coast')
                self.result = self.result.set_index('date_time').resample('15S').first().reset_index()
                self.result.drop(columns='flag', inplace=True)
                self.result["institution"] = 'jason3'
                self.result["data_type"] = 'altimeter'
                self.db.feed_bd(table='data_no_stations', df=self.result, data_type='altimeter')
                print('ok')

            os.remove(f)


    def get_nc_files(self):
        self.nc_files = []
        for file in glob.glob(f"{self.path}/*.nc", recursive=True):
            self.nc_files.append(os.path.abspath(file))

        index = []
        for file_name in self.nc_files:
            index.append(int(file_name.split('/')[-1][16:19]))

        self.nc_files = list(pd.DataFrame(np.array([index,self.nc_files]).T).set_index(0).sort_index()[1])


    def download_ftplib_nodc(self):


        response = requests.get(self.url + self.directory)

        soup = BeautifulSoup(response.text,'html.parser')

        url2 = soup.find_all('td')[-4].text
        response = requests.get(self.url + self.directory + url2)
        soup = BeautifulSoup(response.text,'html.parser')
        links = soup.find_all('a')[5:]

        file_names = []
        for link in links:
            file_names.append(link.text)
        value = f".*{self.start_date.strftime('%Y%m%d')}.*"
        file_names_filter = list(filter(lambda v: re.match(value, v), file_names))

        for file_name in file_names_filter:
            print(file_name)
            urllib.request.urlretrieve(self.url + self.directory + url2 + file_name, f"{self.path}/{file_name}")

        if self.start_date.day != self.end_date.day:
            value = f".*{self.end_date.strftime('%Y%m%d')}.*"
            file_names_filter = list(filter(lambda v: re.match(value, v), file_names))
            for file_name in file_names_filter:
                print(file_name)
                urllib.request.urlretrieve(self.url + self.directory + url2 + file_name, f"{self.path}/{file_name}")

if __name__ == '__main__':
    Altimeter().get()
