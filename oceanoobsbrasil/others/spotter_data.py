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

class Spotter():

    load_dotenv()
    os.environ['WF_API_TOKEN'] = os.getenv("SOFAR_TOKEN")
    
    def __init__(self):

        self.api = SofarApi()
        self.devices = self.api.devices
        self.ids = self.api.device_ids
        self.spotters = self.api.get_spotters()

    def get_new_data(self,
                     start_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d'),
                     end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')):


        self.start_date = start_date
        self.end_date = end_date

        self.data = pd.DataFrame()
        self.data_status = pd.DataFrame()
        
        for spotter in self.spotters:
            if spotter.id in self.working_buoys:
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

                self.result = self.merge_values(wind, wave, sst, spotter)
                if not self.result.empty:
                    self.result['spotter_id'] = spotter.id
                    if self.data.empty:
                        self.data = self.result
                    else:
                        self.data = pd.concat([self.data, self.result])

                self.status = self.get_last_status(spotter)
                if not self.status.empty:
                    if self.data_status.empty:
                        self.data_status = self.status
                    else:
                        self.data_status = pd.concat([self.data_status, self.status])

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
                                            how='outer').merge(sst_spotter,
                                                on = 'timestamp',
                                                how = 'outer')

        spotter_general.rename(columns = {'speed': 'wspd',
                                        'direction': 'wdir',
                                        'significantWaveHeight' : 'swvht',
                                        'degrees':'sst',
                                        'timestamp': 'date_time'
                                        }, inplace = True)

        spotter_general = spotter_general.replace({np.nan:None})

        return spotter_general
    
    def get_last_status(self, spotter):
        
        spotter_id = spotter.id
        lon = (spotter.lon + 180) % 360 - 180
        lat = spotter.lat
        date_time = datetime.strptime(spotter.timestamp, '%Y-%m-%dT%H:%M:%S.000Z')
        solar_v = float(spotter.solar_voltage)
        battery_p = float(spotter.battery_power)
        humidity = float(spotter.humidity)
        battery_v = float(spotter.battery_voltage)

        status_values = {'spotter_id': [id],
                        'timestamp': [date],
                        'latitude': [lat],
                        'longitude': [lon],
                        'battery_power': [battery_p],
                        'battery_voltage': [battery_v],
                        'humidity': [humidity],
                        'solar_voltage': [solar_v]}

        status_spotter = pd.DataFrame(status_values)
        
        return status_spotter