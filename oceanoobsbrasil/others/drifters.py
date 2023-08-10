import datetime
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

from oceanoobsbrasil.db import GetData


class Drifter:
    def __init__(
        self,
        min_lat=-89,
        max_lat=15,
        min_lon=-90,
        max_lon=20,
        start_date=datetime.strftime(
            datetime.now() - timedelta(days=6), format="%Y-%m-%dT00:00:00Z"
        ),
        platform_type="DRIFTING BUOYS (GENERIC)",
    ):
        self.db = GetData()
        self.url = "http://osmc.noaa.gov/erddap/tabledap/OSMC_30day.htmlTable?platform_code,platform_type,time,latitude,longitude,observation_depth,sst,atmp,ztmp,slp,wvht"

        if platform_type == "DRIFTING BUOYS (GENERIC)":
            self.data_type = "drifter"
        else:
            self.data_type = "float"
        self.params = [
            f'platform_type="{platform_type}"',
            f"time>={start_date}",
            f"latitude>={min_lat}",
            f"latitude<={max_lat}",
            f"longitude>={min_lon}",
            f"longitude<={max_lon}",
        ]
        for param in self.params:
            self.url = self.url + "&" + param

    def get(self, save_bd=True):
        resp = requests.get(self.url)

        df = pd.read_html(resp.content)
        df = df[1]
        df.columns = df.columns.droplevel(level=1)
        df = df.loc[df["observation_depth"] >= -1]
        df.sst.fillna(df.ztmp.dropna(), inplace=True)
        df = df[
            [
                "platform_code",
                "time",
                "latitude",
                "longitude",
                "sst",
                "atmp",
                "slp",
                "wvht",
            ]
        ]
        df.columns = ["name", "date_time", "lat", "lon", "sst", "atmp", "pres", "swvht"]
        df["date_time"] = pd.to_datetime(df["date_time"], format="%Y-%m-%dT%H:%M:%SZ")
        df.fillna(np.nan, inplace=True)
        self.result = df
        if save_bd:
            self.result["institution"] = "gdp"
            self.result["data_type"] = self.data_type

            self.db.feed_bd(
                table="data_no_stations", df=self.result, data_type=self.data_type
            )
        else:
            return self.result


if __name__ == "__main__":
    Drifter().get(save_bd=True)
