import requests
import datetime as dt 
import pandas as pd 
from db.db_oceanObs import db_oceanObs as db

points = pd.read_csv("mur/pontos_mur_cptec.csv")

# lon transforming...
points['Lon'] = (points['Lon'] + 180) % 360 - 180

mur_last_date = db.last_data('mur')

if mur_last_date == None:
    start_date = dt.datetime.today() - dt.timedelta(days=3)
else:
    mur_last_date = mur_last_date + dt.timedelta(days=1)
    start_date = datetime.strftime(mur_last_date, format = "%Y-%m-%dT%H:%M:%SZ")

end_date = dt.datetime.today().replace(microsecond=0, second=0, minute=0, hour=9) - dt.timedelta(days=1)
end_date = dt.datetime.strftime(end_date, format = "%Y-%m-%dT%H:%M:%SZ")

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
