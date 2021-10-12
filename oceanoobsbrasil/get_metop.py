
from erddapy import ERDDAP
import pandas as pd
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData


class Metop():

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

        if start_date:
            self.start_date = start_date
        else:
            self.start_date = datetime.strftime(datetime.utcnow()-timedelta(days=1), "%Y-%m-%dT%H:%M:%S")

        if end_date:
            self.end_date = end_date
        else:
            self.end_date = datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S")

        self.dataset_id=dataset_id
        self.server = server


    def get(self, save_bd=False):

        e = ERDDAP(
            server = self.server,
            protocol = "griddap",
            response = "opendap"
        )
        print('ok')

        # Adjust parameters to download
        e.dataset_id = self.dataset_id
        e.griddap_initialize()
        e.response = "csv"
        print('ok')
        # params
        e.constraints['time>='] = self.start_date #'2021-08-08T00:00:00Z'
        e.constraints['time<='] = self.end_date #'2021-08-08T00:00:00Z'
        e.constraints['latitude>='] = self.lat[0]
        e.constraints['latitude<='] = self.lat[1]
        e.constraints['latitude_step'] = self.lat_step
        e.constraints['longitude>='] = self.lon[0]
        e.constraints['longitude<='] = self.lon[1]
        e.constraints['longitude_step'] = self.lon_step
        print('ok')


        self.result = e.to_pandas()

        self.result.columns = ['date_time', 'altitude', 'lat', 'lon', 'x_wind', 'y_wind']

        if save_bd:
            self.result["institution"] = 'metop'
            self.result["data_type"] = 'satellite'

            self.feed_bd()
        else:
            return self.result

    def feed_bd(self):

        self.db.post(table='data_no_stations', df=self.result, data_type='satellite')

