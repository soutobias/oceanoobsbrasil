import datetime
import json
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from oceanoobsbrasil.db import GetData


class Wave:
    def __init__(self, equip="visual"):
        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(
            table="stations",
            institution=["=", "wavecheck"],
            data_type=["=", self.equip],
        )

    def get(self):
        for index, station in self.stations.iterrows():
            response = requests.get(station["url"])

            soup = BeautifulSoup(response.text, "html.parser")
            no_data = soup.find("p", {"class": "alerta-pico-desatualizado"})
            print(station["name"])
            if not no_data:
                print("Tem dados para esse pico")

                l = soup.find("td", {"id": "forecast_wave_size"}).get_text(strip=True)
                try:
                    [k1, k2] = l.split("m")
                    swvht = float(k1)
                except:
                    swvht = 0

                l = soup.find("td", {"id": "forecast_wave_direction"}).get_text(
                    strip=True
                )
                wvdir = str(l).lower()
                if wvdir == "norte":
                    wvdir = 0
                if wvdir == "norte-nordeste" or wvdir == "norte nordeste":
                    wvdir = 22
                if wvdir == "nordeste":
                    wvdir = 45
                if (
                    wvdir == "nordeste-leste"
                    or wvdir == "nordeste leste"
                    or wvdir == "leste nordeste"
                    or wvdir == "leste-nordeste"
                ):
                    wvdir = 45 + 22
                if wvdir == "leste":
                    wvdir = 90
                if (
                    wvdir == "sudeste-leste"
                    or wvdir == "sudeste leste"
                    or wvdir == "leste sudeste"
                    or wvdir == "leste sudeste"
                ):
                    wvdir = 90 + 22
                if wvdir == "sudeste":
                    wvdir = 90 + 45
                if (
                    wvdir == "sul-sudeste"
                    or wvdir == "sul sudeste"
                    or wvdir == "sudeste sul"
                    or wvdir == "sudeste-sul"
                ):
                    wvdir = 90 + 45 + 22
                if wvdir == "sul":
                    wvdir = 180
                if (
                    wvdir == "sul-sudoeste"
                    or wvdir == "sul sudoeste"
                    or wvdir == "sudoeste-sul"
                    or wvdir == "sudoeste sul"
                ):
                    wvdir = 180 + 22
                if wvdir == "sudoeste":
                    wvdir = 180 + 45
                if (
                    wvdir == "sudoeste-oeste"
                    or wvdir == "sudoeste oeste"
                    or wvdir == "oeste-sudoeste"
                    or wvdir == "oeste sudoeste"
                ):
                    wvdir = 180 + 45 + 22
                if wvdir == "oeste":
                    wvdir = 270
                if (
                    wvdir == "noroeste-oeste"
                    or wvdir == "noroeste oeste"
                    or wvdir == "oeste-noroeste"
                    or wvdir == "oeste noroeste"
                ):
                    wvdir = 270 + 22
                if wvdir == "noroeste":
                    wvdir = 270 + 45
                if (
                    wvdir == "noroeste-norte"
                    or wvdir == "noroeste norte"
                    or wvdir == "norte-noroeste"
                    or wvdir == "norte noroeste"
                ):
                    wvdir = 270 + 45 + 22
                if wvdir == "não informado":
                    wvdir = np.nan

                date_time = datetime.now()
                date_time = date_time.replace(minute=0, second=0, microsecond=0)

                values = np.array([date_time, swvht, wvdir])
                columns = ["date_time", "swvht", "wvdir"]

                self.result = pd.DataFrame(values).T
                self.result.columns = columns
                self.result["station_id"] = str(station["id"])
                self.db.feed_bd(table="data_stations", df=self.result)
                print("dados alimentados")
            else:
                print("No data for this station")


if __name__ == "__main__":
    Wave().get()
