"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import datetime
import json
import os
import time
from datetime import datetime, timedelta
from re import A

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from oceanoobsbrasil.db import GetData


class GlossTide:
    load_dotenv()

    def __init__(
        self,
        equip="tide",
        start_date=(datetime.utcnow() - timedelta(days=1)).strftime(
            "%Y-%m-%d 00:00:00"
        ),
        end_date=(datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d 00:00:00"),
    ):
        # Connect to the database

        if datetime.utcnow() - timedelta(days=1) < datetime(2022, 6, 7, 9, 0, 0):
            start_date = datetime(2022, 6, 7, 9, 0, 0).strftime("%Y-%m-%d %H:00:00")
        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(
            table="stations", institution=["=", "gloss"], data_type=["=", self.equip]
        )

    def get(self):
        for index, station in self.stations.iterrows():
            query = {
                "startTime": self.start_date,
                "endTime": self.end_date,
                "stationId": str(station.url),
                "sensorName": "RLS",
            }
            headers = {
                "clientId": os.getenv("GLOSS_CLIENT"),
                "api-key": os.getenv("GLOSS_APIKEY"),
            }

            response = requests.get(
                "http://www.hydrometcloud.com:8080/Data/rest/api/sensordata",
                params=query,
                headers=headers,
            )
            data = response.json()["sensorData"]
            self.data = pd.DataFrame(data)

            query["sensorName"] = "SE200"
            response = requests.get(
                "http://www.hydrometcloud.com:8080/Data/rest/api/sensordata",
                params=query,
                headers=headers,
            )
            data = response.json()["sensorData"]
            self.data2 = pd.DataFrame(data)

            self.data.set_index("sampleTime", inplace=True)
            self.data2.set_index("sampleTime", inplace=True)

            self.result = pd.concat(
                [self.data, self.data2], axis=1, join="inner"
            ).reset_index()

            self.result.columns = ["date_time", "water_level", "water_level_2"]

            if len(self.result) == 0:
                print("Nao ha dados para essa estacao")
            else:
                self.result["date_time"] = pd.to_datetime(self.result.date_time)
                self.result = self.result.replace(
                    to_replace=["None", "NULL", " ", ""], value=np.nan
                )
                self.result["station_id"] = str(station["id"])
                self.db.feed_bd(table="data_stations", df=self.result)


if __name__ == "__main__":
    GlossTide().get()
