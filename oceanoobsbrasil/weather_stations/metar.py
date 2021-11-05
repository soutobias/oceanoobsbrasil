

import time

import requests
import io

import numpy as np

import pandas as pd
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData

class Metar():
    def __init__(self, equip='meteorological_station',
        start_date=datetime.utcnow()-timedelta(days=3),
        end_date=datetime.utcnow()):
        # Connect to the database

        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(table='stations', institution=['=', 'metar'], data_type=['=', self.equip])

    def get(self, save_bd=True):
        self.url = f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=SBAF&station=SBAR&station=SBBE&station=SBCB&station=SBCV&station=SBFL&station=SBFS&station=SBFZ&station=SBGL&station=SBIL&station=SBJE&station=SBJP&station=SBJR&station=SBJV&station=SBME&station=SBMO&station=SBMQ&station=SBNF&station=SBNT&station=SBPB&station=SBPG&station=SBPS&station=SBRF&station=SBRG&station=SBRJ&station=SBSC&station=SBSL&station=SBST&station=SBSV&station=SBTC&station=SBVT&data=tmpc&data=vsby&data=dwpc&data=relh&data=drct&data=sknt&year1={self.start_date.year}&month1={self.start_date.month}&day1={self.start_date.day}&year2={self.end_date.year}&month2={self.end_date.month}&day2={self.end_date.day}&tz=Etc%2FUTC&format=onlycomma&latlon=no&elev=no&missing=empty&trace=empty&direct=no&report_type=1&report_type=2"

        url_data = requests.get(self.url).content
        df = pd.read_csv(io.StringIO(url_data.decode('utf-8')))
        df.columns = ['name','date_time','atmp', 'visibility', 'dewpt', 'rh', 'wdir', 'wspd']

        self.stations['station_id'] = self.stations['id']
        self.result = self.stations[['station_id', 'name']].merge(df, on='name')

        if len(self.result) == 0:
            print ("Nao ha dados para essa boia")
        else:
            self.result['date_time'] = pd.to_datetime(self.result['date_time'])
            self.result.drop(columns=['name'], inplace=True)

            self.result = self.result.replace(to_replace =['None', 'NULL', ' ', ''],
                                    value =np.nan)
            print('ok')
            if save_bd:
                self.db.feed_bd(table='data_stations', df=self.result)
            else:
                return self.result

if __name__ == '__main__':
    Metar().get(save_bd=True)
