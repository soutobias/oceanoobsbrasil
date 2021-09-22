import requests
import pandas as pd
from datetime import datetime, timedelta
from oceanoobsbrasil.bd import GetData


class Mur():

    def __init__(self,
        lat=[-36, 8],
        lat_step=4,
        lon=[-50, -20],
        lon_step=4,
        dataset_id="erdQMwind1day_LonPM180",
        server="CSWC",
        start_date=None,
        end_date=None):

        self.db = GetData()
        self.lat = lat
        self.lon = lon
        self.lat_step = lat_step
        self.lon_step = lon_step

        self.points = self.load_point()

        start_date = datetime.strftime(datetime.today() - dt.timedelta(days=5), format = "%Y-%m-%dT%H:%M:%SZ")

        mur_last_date = self.bd.get(table='data_no_stations', start_date=start_date, institution=['=', 'mur'])

        if mur_last_date.empty():
            self.start_date = start_date
        else:
            mur_last_date = self.mur_db.sort_values(by='date_time', ascending=False)
            self.start_date = datetime.strftime(mur_last_date['date_time'].iloc[0] + timedelta(days=1), format = "%Y-%m-%dT%H:%M:%SZ")

        self.end_date = datetime.today().replace(microsecond=0, second=0, minute=0, hour=9) - timedelta(days=1)
        self.end_date = datetime.strftime(end_date, format = "%Y-%m-%dT%H:%M:%SZ")

        all_points = pd.DataFrame()

        for index, point in points.iterrows():
            print(f"Ponto {index}.")
            lat = round(point['Lat'],4)
            lon = round(point['Lon'],4)

            r = requests.get(f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json?analysed_sst%5B({start_date}):1:({end_date})%5D%5B({lat}):1:({lat})%5D%5B({lon}):1:({lon})%5D")
            json_file = r.json()

            df = pd.json_normalize(json_file, record_path=["table", "rows"])
            all_points = all_points.append(df)
            print(df)


        all_points.columns = ['date_time', 'lat','lon','sst']


        # insert data on db
        status_insert = db.insert_data_mur(all_points)


    def load_point(self):
        points = pd.read_csv("data/pontos_mur_cptec.csv")

        points['lon'] = (points['Lon'] + 180) % 360 - 180

        return points
