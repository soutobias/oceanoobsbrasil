import requests
import pandas as pd
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *


class Mur():

    def __init__(self,
        start_date=datetime.strftime(datetime.utcnow() - timedelta(days=3), format = "%Y-%m-%dT%H:%M:%SZ"),
        end_date=datetime.strftime(datetime.utcnow() + timedelta(days=1), format = "%Y-%m-%dT%H:%M:%SZ")):

        self.db = GetData()
        self.points = mur_points()
        self.mur_last_date = self.db.get(table='data_no_stations', start_date=start_date, institution=['=', 'mur'])

        if self.mur_last_date.empty:
            self.start_date = start_date
        else:
            mur_last_date = self.mur_db.sort_values(by='date_time', ascending=False)
            self.start_date = datetime.strftime(mur_last_date['date_time'].iloc[0] + timedelta(days=1), format = "%Y-%m-%dT%H:%M:%SZ")

        self.end_date = end_date

    def get(self):

        self.result = pd.DataFrame()

        for index, point in self.points.iterrows():
            print(f"Ponto {index}.")
            lat = round(point['Lat'],4)
            lon = round(point['Lon'] - 360,4)

            r = requests.get(f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json?analysed_sst%5B({self.start_date}):1:({self.end_date})%5D%5B({lat}):1:({lat})%5D%5B({lon}):1:({lon})%5D")
            json_file = r.json()

            df = pd.json_normalize(json_file, record_path=["table", "rows"])
            self.result = self.result.append(df)
            print(df)

        self.result.columns = ['date_time', 'lat','lon','sst']
        self.result["institution"] = 'mur'
        self.result["data_type"] = 'mur'
        self.db.feed_bd(table='data_no_stations', df=self.result, data_type='mur')

if __name__ == '__main__':
    Mur().get()
