
import pandas as pd
import numpy as np

from datetime import datetime, timedelta
import time

from oceanoobsbrasil.db import GetData

import glob, os, subprocess, shlex
import ftplib
from netCDF4 import Dataset


class Altimeter():

    def __init__(self,
        start_date=datetime.utcnow()-timedelta(days=1),
        end_date=datetime.utcnow(),
        directory='pub/data.nodc/jason3/ogdr/ogdr/',
        url='ftp.nodc.noaa.gov',
        lat=[-36, 8],
        lon=[-50, -20]):


        self.directory = directory
        self.start_date = start_date
        self.end_date = end_date
        self.url = url

        self.db = GetData()
        self.lat = lat
        self.lon = lon

        self.path = f"{os.path.dirname(__file__)}/data"

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


            ar = np.array([tempo, lat, lon, wspd, swvht])
            df = pd.DataFrame(ar).T

            columns = ['date_time', 'lat', 'lon', 'wspd', 'swvht']
            df.columns = columns

            df.lon = df.lon - 180
            df.date_time = df.date_time + time_2000_1970
            df.date_time = pd.to_datetime(df['date_time'],unit='s')
            df = df[(df.lat > self.lat[0]) & (df.lat < self.lat[1]) & (df.lon < self.lon[1]) & (df.lon > self.lon[0])]
            self.result = df[(df.wspd < 9999) & (df.swvht < 9999)]

            if not self.result.empty:
                print('data for brazilian coast')
                self.result = self.result.set_index('date_time').resample('15S').first().reset_index()
                self.result["institution"] = 'jason3'
                self.result["data_type"] = 'altimeter'
                self.feed_bd()

            os.remove(f)

    def feed_bd(self):

        self.db.post(table='data_no_stations', df=self.result, data_type='altimeter')


    def get_nc_files(self):
        self.nc_files = []
        for file in glob.glob(f"{self.path}/*.nc", recursive=True):
            self.nc_files.append(os.path.abspath(file))


    def download_ftplib_nodc(self):

        ftp = ftplib.FTP(self.url)
        ftp.login('','')
        ftp.cwd(self.directory)

        dir_list = []
        ftp.dir(dir_list.append)
        directory2 = dir_list[-1].split(' ')[-1]
        ftp.cwd(directory2)

        filematch = f"JA3_OPN_*{self.start_date.strftime('%Y%m%d')}*.nc"
        for filename in ftp.nlst(filematch):
            fhandle = open(f"{self.path}/{filename}", 'wb')
            print ('Getting ' + filename)
            ftp.retrbinary('RETR ' + filename, fhandle.write)
            fhandle.close()

        if self.start_date.day != self.end_date.day:
            filematch = f"JA3_OPN_*{self.end_date.strftime('%Y%m%d')}*.nc"
            for filename in ftp.nlst(filematch):
                fhandle = open(f"{self.path}/{filename}", 'wb')
                print ('Getting ' + filename)
                ftp.retrbinary('RETR ' + filename, fhandle.write)
                fhandle.close()
