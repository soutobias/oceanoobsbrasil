import datetime
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from oceanoobsbrasil.db import GetData


class Pnboia:
    load_dotenv()

    def __init__(
        self,
        equip="buoy",
        start_date=(datetime.utcnow() - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),
        end_date=(datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    ):
        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(
            table="stations", institution=["=", "pnboia"], data_type=["=", self.equip]
        )

    def get(self, save_bd=True):
        for index, station in self.stations.iterrows():
            url = f"http://52.67.222.63/v1/qualified_data/qualified_data?buoy_id={station['url']}&start_date={self.start_date}&end_date={self.end_date}&token={os.getenv('REMOBS_TOKEN')}"
            response = requests.get(url).json()
            print(station["name"], station["url"])
            # print(response)
            try:
                df = pd.DataFrame(response)
                for i in df.columns:
                    try:
                        df[i] = pd.to_numeric(df[i])
                    except:
                        pass
                df["date_time"] = pd.to_datetime(
                    df["date_time"], format="%Y-%m-%dT%H:%M:%S"
                )
                df.sort_values("date_time", inplace=True)
                if station["url"] in [31, 32]:
                    print(station)
                    df = df[df["swvht1"].notna()]

                df = df[
                    [
                        "date_time",
                        "rh",
                        "pres",
                        "atmp",
                        "dewpt",
                        "wspd1",
                        "wdir1",
                        "gust1",
                        "sst",
                        "swvht1",
                        "mxwvht1",
                        "tp1",
                        "wvdir1",
                    ]
                ]

                df.columns = [
                    "date_time",
                    "rh",
                    "pres",
                    "atmp",
                    "dewpt",
                    "wspd",
                    "wdir",
                    "gust",
                    "sst",
                    "swvht",
                    "mxwvht",
                    "tp",
                    "wvdir",
                ]

                self.result = df.copy()

                if len(self.result) == 0:
                    print("Nao ha dados para essa boia")
                else:
                    self.result.wspd = self.result.wspd * 1.94384
                    self.result.gust = self.result.gust * 1.94384

                    self.result = self.result.replace(
                        to_replace=["None", "NULL", " ", ""], value=np.nan
                    )
                    if save_bd:
                        self.result["station_id"] = str(station["id"])
                        self.db.feed_bd(table="data_stations", df=self.result)
                    else:
                        return self.result
                    print("Dados inseridos")
            except Exception as e:
                print(str(e))
                continue


if __name__ == "__main__":
    Pnboia().get(save_bd=True)
