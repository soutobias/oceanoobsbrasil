import datetime
import json
import re
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from oceanoobsbrasil.db import GetData


class Ndbc:
    # def __init__(self, lat=[-35.8333, 7],
    #     lon=[-55.20, 20],
    #     hours=12):
    def __init__(self, lat=[-15], lon=[-18], hours=12):
        self.db = GetData()
        self.lat = lat
        self.lon = lon
        self.hours = hours

        self.start_date = datetime.utcnow() - timedelta(hours=self.hours)
        self.end_date = datetime.utcnow()
        self.url = f"https://www.ndbc.noaa.gov/ship_obs.php?uom=M&time=12"

    def get(self, save_bd=True):
        resp = requests.get(self.url)

        soup = BeautifulSoup(resp.text, "html.parser")

        lines = soup.find_all("pre")
        data = []
        first_loop = True
        for line in lines:
            inner_lines = line.find_all('span')
            first_element = 1
            for inner_line in inner_lines:
                if first_element:
                    first_element = 0
                    new_header = inner_line.get_text(strip=True)
                    new_header = new_header.replace("B", " B")
                    new_header = re.sub(" +", ",", new_header).split(",")
                else:
                    new_data = inner_line.get_text(strip=True)
                    new_data = new_data.replace("B", " B")
                    new_data = re.sub(" +", ",", new_data).split(",")
                    data.append(new_data)
            if first_loop:
                first_loop = False
                df = pd.DataFrame(data)
            else:
                array = pd.DataFrame(data)

                df = pd.concat([df, array])
                
        df.columns = new_header[:25]
        df.replace("-", np.nan, inplace=True)

        df['HOUR'] = (df['HOUR'].astype(int) / 100).astype(int)
        df["date_time"] = df['HOUR'].apply(lambda x: self.calculate_date(x))
        self.result = df[
            [
                "SHIP",
                "date_time",
                "LAT",
                "LON",
                "WDIR",
                "WSPD",
                "WVHT",
                "DPD",
                "PRES",
                "ATMP",
                "WTMP",
                "DEWP",
                "S1HT",
                "S1DIR",
            ]
        ].copy()
        self.result.columns = [
            "name",
            "date_time",
            "lat",
            "lon",
            "wdir",
            "wspd",
            "swvht",
            "tp",
            "pres",
            "atmp",
            "sst",
            "dewpt",
            "swvht_swell",
            "wvdir_swell",
        ]

        self.convert_to_numeric()
        self.result.wspd[self.result.wspd.notnull()] = (
            self.result.wspd[self.result.wspd.notnull()] * 1.94384
        ).round(decimals=1)
        self.result = self.result[(self.result.lat>-40)  & (self.result.lat < 15) & (self.result.lon < -8) & (self.result.lon > -60)]
        if save_bd:
            self.result["institution"] = "ndbc"
            self.result["data_type"] = "gts"

            self.db.feed_bd(table="data_no_stations", df=self.result, data_type="gts")
        else:
            return self.result

    def calculate_date(self, x):
        start_date = datetime.utcnow() - timedelta(hours=12)
        end_date = datetime.utcnow()
        if x >= end_date.hour + 2:
            value = start_date
            value = value.replace(hour=x)
        else:
            value = end_date
            value = value.replace(hour=x)

        value = value.replace(minute=0)
        value = value.replace(second=0)
        value = value.replace(microsecond=0)
        return value

    def convert_to_numeric(self):
        columns = self.result.drop(columns=["date_time", "name"]).columns
        for column in columns:
            self.result[column] = pd.to_numeric(self.result[column], errors="coerce")


if __name__ == "__main__":
    Ndbc().get(save_bd=True)
