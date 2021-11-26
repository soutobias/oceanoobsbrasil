import pandas as pd
import xarray as xr
import numpy as np

from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData

from podaac import podaac
from podaac import podaac_utils as utils
from podaac import drive as drive
from podaac import l2ss
import os
import glob

from os.path import expanduser

from dotenv import load_dotenv

class Metop():

    load_dotenv()

    def __init__(self,
        lat=[-35, 7],
        lon=[-55, -20],
        step=20,
        webdav_url = 'https://podaac-tools.jpl.nasa.gov/drive/files',
        datasets = ['PODAAC-ASOP2-25X01', 'PODAAC-ASOP2-25B01', 'PODAAC-ASOP2-25C01'],
        start_date = datetime.strftime(datetime.utcnow()-timedelta(days=2), "%Y-%m-%dT%H:%M:%SZ"),
        end_date = datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%SZ")):

        self.db = GetData()
        home = expanduser("~")
        self.path = f"{home}/data"
        self.lat = lat
        self.lon = lon
        self.step = step
        self.start_date = start_date
        self.end_date = end_date

        self.datasets = datasets

        self.webdav_url = webdav_url
        self.username=os.getenv('PODAAC_USR')
        self.password=os.getenv('PODAAC_PWD')


    def get(self):

        wind_flag = pd.DataFrame([], dtype = 'float64')
        wind_dir = pd.DataFrame([], dtype = 'float64')
        wind_speed = pd.DataFrame([], dtype = 'float64')
        wind_time = pd.DataFrame([], dtype = 'float64')
        wind_lat = pd.DataFrame([], dtype = 'float64')
        wind_lon = pd.DataFrame([], dtype = 'float64')

        self.get_nc_files()

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

    def download(self):

        p = podaac.Podaac()
        u = utils.PodaacUtils()

        d = drive.Drive(file = '', username=self.username, password=self.password, webdav_url=self.webdav_url)

        box = ','.join([str(self.lon[0]), str(self.lat[0]), str(self.lon[1]), str(self.lat[1])])

        for dataset in self.datasets:
            print(dataset)
            newData = p.granule_search(dataset_id = dataset,
                                    start_time = self.start_date,
                                    end_time = self.end_date,
                                    bbox = box,
                                    sort_by = 'timeAsc',
                                    items_per_page = '400',
                                    _format = 'atom')


            if newData:
                granules = d.mine_drive_urls_from_granule_search(granule_search_response = (str(newData)))
                list_granules = u.mine_granules_from_granule_search(granule_search_response=str(newData))

                l = l2ss.L2SS()

                query = {
                    "email": '',
                    'query':
                    [
                        {
                            "compact": "false",
                            "datasetId": dataset,
                            "bbox": box,
                            "variables": ["lat","lon","time","wind_speed","wind_dir","wvc_quality_flag"],
                            "granuleIds": list_granules
                        }
                    ]
                }
                os.chdir(self.path)

                l.granule_download(query_string = query, path=self.path)

    def get_nc_files(self):
        self.nc_files = []
        for file in glob.glob(f"{self.path}/*l2.nc", recursive=True):
            self.nc_files.append(os.path.abspath(file))

if __name__ == '__main__':
    Metop().get()
