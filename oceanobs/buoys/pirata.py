import datetime
import json
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from oceanoobsbrasil.db import GetData


class Pirata:
    def __init__(self, equip="buoy"):
        self.db = GetData()
        self.equip = equip
        self.url = "https://www.ndbc.noaa.gov/data/realtime2/"
        self.stations = self.db.get(
            table="stations", institution=["=", "pirata"], data_type=["=", self.equip]
        )

    def get(self, save_bd=True):
        for index, station in self.stations.iterrows():
            print(station.url)
            url_address = f"{self.url}{station['url']}.txt"
            try:
                with urllib.request.urlopen(url_address) as url:
                    df = pd.read_csv(url, sep="\s+")
                    df = df.iloc[1:]
                self.result = df

                rename_columns = {
                    "#YY": "year",
                    "MM": "month",
                    "DD": "day",
                    "hh": "hour",
                    "mm": "minute",
                }
                self.result.rename(columns=rename_columns, inplace=True)
                self.result["date_time"] = pd.to_datetime(self.result.iloc[:, 0:4])

                self.result = self.result[
                    [
                        "date_time",
                        "WDIR",
                        "WSPD",
                        "GST",
                        "WVHT",
                        "DPD",
                        "MWD",
                        "PRES",
                        "ATMP",
                        "WTMP",
                        "DEWP",
                        "VIS",
                    ]
                ]

                self.result.columns = [
                    "date_time",
                    "wdir",
                    "wspd",
                    "gust",
                    "swvht",
                    "tp",
                    "wvdir",
                    "pres",
                    "atmp",
                    "sst",
                    "dewpt",
                    "visibility",
                ]

                self.result = self.result.replace(
                    to_replace=["None", "NULL", "MM", ""], value=np.nan
                )

                self.convert_to_numeric()
                self.result.wspd[self.result.wspd.notnull()] = (
                    self.result.wspd[self.result.wspd.notnull()] * 1.94384
                ).round(decimals=1)
                self.result.gust[self.result.gust.notnull()] = (
                    self.result.gust[self.result.gust.notnull()] * 1.94384
                ).round(decimals=1)

                if save_bd:
                    self.result["station_id"] = str(station["id"])
                    self.db.feed_bd(table="data_stations", df=self.result)
                    print("ok")
                else:
                    return self.result
            except:
                print("Nao ha dados para essa boia")

    def convert_to_numeric(self):
        columns = self.result.drop(columns="date_time").columns
        for column in columns:
            self.result[column] = pd.to_numeric(self.result[column], errors="coerce")


if __name__ == "__main__":
    Pirata().get(save_bd=True)
