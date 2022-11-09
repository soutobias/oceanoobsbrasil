import pandas as pd
import xarray as xr
import numpy as np
import tempfile

from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData

from harmony import BBox, Client, Collection, Request, Environment, LinkType
import os
import glob

from dotenv import load_dotenv

class Metop():

    load_dotenv()

    def __init__(self,
        b_box=(-55,-35,20,7),
        step=20,
        datasets = ['C2075141559-POCLOUD'],
        start_date = datetime.utcnow()-timedelta(days=2),
        end_date = datetime.utcnow()+timedelta(days=1)):

        self.db = GetData()
        self.b_box = BBox(b_box[0], b_box[1], b_box[2], b_box[3])
        self.step = step
        self.start_date = start_date
        self.end_date = end_date

        self.datasets = datasets

        self.username=os.getenv('EDL_USR')
        self.password=os.getenv('EDL_PWD')


    def get(self):

        wind_flag = pd.DataFrame([], dtype = 'float64')
        wind_dir = pd.DataFrame([], dtype = 'float64')
        wind_speed = pd.DataFrame([], dtype = 'float64')
        wind_time = pd.DataFrame([], dtype = 'float64')
        wind_lat = pd.DataFrame([], dtype = 'float64')
        wind_lon = pd.DataFrame([], dtype = 'float64')

        for collection in self.datasets:
            self.download(collection)
            for f in  self.nc_files:
                print(f)
                ds = xr.open_dataset(f)
                wind_flag = wind_flag.append(pd.DataFrame(ds['wvc_quality_flag'].values))
                wind_dir = wind_dir.append(pd.DataFrame(ds['wind_dir'].values))
                wind_speed = wind_speed.append(pd.DataFrame(ds['wind_speed'].values))
                wind_time = wind_time.append(pd.DataFrame(ds['time'].values))
                wind_lat = wind_lat.append(pd.DataFrame(ds['lat'].values))
                wind_lon = wind_lon.append(pd.DataFrame(ds['lon'].values))
                os.remove(f)

        date_time = np.array(pd.melt(wind_time, value_name = 'date_time')['date_time'])
        wdir = np.array(pd.melt(wind_dir, value_name = 'wdir')['wdir'])
        wspd = np.array(pd.melt(wind_speed, value_name = 'wspd')['wspd'])
        lat = np.array(pd.melt(wind_lat, value_name = 'lat')['lat'])
        lon = np.array(pd.melt(wind_lon, value_name = 'lon')['lon'])

        win_flag = np.array(pd.melt(wind_flag, value_name = 'win_flag')['win_flag'])
        allData = [date_time, lat, lon, wdir, wspd, win_flag]

        df = pd.DataFrame(allData).T
        df.columns = ['date_time', 'lat', 'lon', 'wdir', 'wspd', 'flag']
        df = df[df['flag'] == 0]
        df.lat = pd.to_numeric(df.lat, errors='coerce').round(decimals=4)
        df.lon = pd.to_numeric(df.lon, errors='coerce').round(decimals=4)
        df.wdir = pd.to_numeric(df.wdir, errors='coerce').round()
        df.wspd = pd.to_numeric(df.wspd, errors='coerce').round(decimals=1)
        df = df.replace(0, np.nan)
        df.drop(columns='flag', inplace=True)
        df.dropna(inplace=True)
        df.lon = df.lon-360
        df = df.iloc[::self.step]

        self.result = df
        print('Verificando se há dados')
        if not self.result.empty:
            print('Há dados')

            self.result["institution"] = 'metop'
            self.result["data_type"] = 'scatterometer'

            self.result.wspd = (self.result.wspd * 1.94384).round(decimals=1)

            self.db.feed_bd(table='data_no_stations', df=self.result, data_type='scatterometer')
        else:
            print('Não há dados')

    def download(self, collection):

        harmony_client = Client(auth=(self.username, self.password))
        collection_id = Collection(collection) 

        request = Request(
            collection=collection_id,
            temporal={
                'start': self.start_date,
                'stop': self.end_date
            },
            spatial=BBox(-55,-35,20,7) #  lat: (-45.75:45), lon: (-90:90)
        )
        if request.is_valid():
            job_id = harmony_client.submit(request)
            print('\n Waiting for the job to finish. . .\n')
            response = harmony_client.result_json(job_id, show_progress=True)
            print("\n. . .DONE!")
        temp_dir = tempfile.mkdtemp()
        futures = harmony_client.download_all(job_id, directory=temp_dir, overwrite=True)
        self.nc_files = [f.result() for f in futures]

if __name__ == '__main__':
    Metop().get()
