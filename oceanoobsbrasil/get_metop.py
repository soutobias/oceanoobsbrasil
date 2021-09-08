
import pandas as pd 
from erddapy import ERDDAP 

server = "CSWC"

e = ERDDAP(
    server = server,
    protocol = "griddap",
    response="opendap"
)t

# Adjust parameters to download
e.dataset_id = "erdQMwind1day_LonPM180"
e.griddap_initialize()
e.response = "csv"
# params
e.constraints['time>='] = start_date #'2021-08-08T00:00:00Z'
e.constraints['time<='] = end_date #'2021-08-08T00:00:00Z'
e.constraints['latitude>='] = -36
e.constraints['longitude<='] = 8
e.constraints['latitude_step'] = 4
e.constraints['longitude<='] = -20
e.constraints['longitude>='] = -50
e.constraints['longitude_step'] = 4


metop_df = e.to_pandas()

metop_df.columns = ['date_time', 'altitude', 'lat', 'lon', 'x_wind', 'y_wind']

metop_df.dropna(inplace=True)
