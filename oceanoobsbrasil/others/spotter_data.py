from ipaddress import collapse_addresses
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from oceanoobsbrasil.db import GetData

import os
import glob
from os.path import expanduser
from dotenv import load_dotenv

from pysofar.sofar import SofarApi
from pysofar.spotter import Spotter

class SpotterData():

    load_dotenv()
    os.environ['WF_API_TOKEN'] = os.getenv("SOFAR_TOKEN")
    
    def __init__(self):

        self.api = SofarApi()
        self.devices = self.api.devices
        self.ids = [x for x in self.api.device_ids if x[0:7] == 'SPOT-01']
        self.spotters = self.api.get_spotters()
        self.db = GetData()


    def get_new_data(self,
                     start_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                     end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d'),
                     save_bd=True):


        self.start_date = start_date
        self.end_date = end_date

        self.result = pd.DataFrame()
        
        for spotter in self.spotters:
            if spotter.id in self.ids:
                print(spotter.id)
                spt_data = spotter.grab_data(
                    limit=100,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    include_track=True,
                    include_wind=True,
                    include_surface_temp_data=True,
                    include_frequency_data=False,
                    include_directional_moments=True
                )

                wind = pd.json_normalize(spt_data, record_path=['wind'], meta=['spotterId'])
                wave = pd.json_normalize(spt_data, record_path=['waves'], meta=['spotterId'])
                if 'surfaceTemp' in spt_data.keys():
                    sst = pd.json_normalize(spt_data, record_path=['surfaceTemp'], meta=['spotterId'])
                else:
                    sst = None

                self.data = self.merge_values(wind, wave, sst, spotter)
                if not self.data.empty:
                    self.data['spotter_id'] = spotter.id
                    if self.result.empty:
                        self.result = self.data
                    else:
                        self.result = pd.concat([self.result, self.data])

        self.result = self.result[['date_time','latitude','longitude','wspd','wdir','swvht','peakPeriod',
                          'meanDirection', 'sst']]
                          
        self.result.columns = ['date_time', 'lat', 'lon', 'wspd', 'wdir', 'swvht', 'tp', 'wvdir','sst']
        self.convert_to_numeric()

        if save_bd:
            self.result["institution"] = 'sofar'
            self.result["data_type"] = 'drifter'
            self.result["flag"] = False

            self.db.feed_bd(table='data_no_stations', df=self.result, data_type='drifter')
        else:
            return self.result

    def merge_values(self, wind, wave, sst, spotter):

        format_date = '%Y-%m-%dT%H:%M:%S.000Z'

        wind_columns = ['speed', 'direction', 'seasurfaceId', 'latitude', 'longitude', 'timestamp']
        
        wave_columns = ['significantWaveHeight', 'peakPeriod', 'meanPeriod',
                                'peakDirection', 'peakDirectionalSpread',
                                'meanDirection', 'meanDirectionalSpread', 'timestamp']
    
        sst_columns = ['degrees','timestamp']
        
        if not wind.empty:
            wind_spotter = wind[wind_columns]
            wind_spotter.loc[:,'timestamp'] = pd.to_datetime(wind.loc[:,'timestamp'], format = format_date)
        else:
            print("No wind data for buoy %s from %s to %s" % (spotter.id, self.start_date, self.end_date))
            wind_spotter = pd.DataFrame(columns=wind_columns)

        if not wave.empty:
            waves_spotter = wave[wave_columns]
            waves_spotter.loc[:,'timestamp'] = pd.to_datetime(waves_spotter.loc[:,'timestamp'], format=format_date)
        else:
            print("No wave data for buoy %s from %s to %s" % (spotter.id, self.start_date, self.end_date))
            waves_spotter = pd.DataFrame(columns=wave_columns)

        if not sst.empty:
            sst_spotter = sst[sst_columns]
            sst_spotter.loc[:,'timestamp'] = pd.to_datetime(sst_spotter.loc[:,'timestamp'], format = format_date)
        else:            
            print("No sst data for buoy %s from %s to %s" % (spotter.id, self.start_date, self.end_date))
            sst_spotter = pd.DataFrame(columns=sst_columns)

        spotter_general = wind_spotter.merge(waves_spotter,
                                            on='timestamp',
                                            how='left').merge(sst_spotter,
                                                on = 'timestamp',
                                                how = 'left')

        spotter_general.rename(columns = {'speed': 'wspd',
                                        'direction': 'wdir',
                                        'significantWaveHeight' : 'swvht',
                                        'degrees':'sst',
                                        'timestamp': 'date_time'
                                        }, inplace = True)

        spotter_general = spotter_general.replace({np.nan:None})

        return spotter_general

    def convert_to_numeric(self):
        columns = self.result.drop(columns='date_time').columns
        for column in columns:
            self.result[column] = pd.to_numeric(self.result[column], errors='coerce')