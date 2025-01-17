"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import os
import re
import time
from datetime import datetime, timedelta

import chromedriver_binary
import numpy as np
import pandas as pd
import psutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *


class EpagriTide:
    def __init__(
        self,
        args=["-headless", "--no-sandbox", "--disable-dev-shm-usage"],
        preferences=[],
        equip="tide",
    ):
        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.options = def_args_prefs(self.options, self.args, self.preferences)
        self.driver = webdriver.Chrome(options=self.options)

        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(
            table="stations", institution=["=", "epagri"], data_type=["=", self.equip]
        )
        self.url = "https://ciram.epagri.sc.gov.br/index.php/maregrafos/"

    def get(self):
        self.driver.get(self.url)
        time.sleep(60)

        table_NM = pd.read_html(self.driver.page_source)
        self.table_NM = table_NM
        self.soup = BeautifulSoup(self.driver.page_source, "html.parser")

        self.sts = []
        values = self.soup.find(attrs={"class": "row"}).find_all(
            attrs={"style": "font-size: 11pt;"}
        )
        for value in values:
            self.sts.append(value.text)

        for index, st in enumerate(self.sts):
            station = self.stations[self.stations.name == st]
            if not station.empty:
                self.result = table_NM[index]
                print(self.result)

                self.result["date_time"] = pd.to_datetime(
                    self.result.Topping, format="%d/%m %H:%M"
                ) + pd.offsets.DateOffset(years=datetime.utcnow().year - 1900)
                self.result = self.result[["Mare Obser.", "Residual", "date_time"]]
                columns = ["water_level", "meteorological_tide", "date_time"]
                self.result.columns = columns

                self.result = self.result.replace(
                    to_replace=["None", "NULL", " ", ""], value=np.nan
                )
                self.result = self.result.loc[
                    np.isnan(self.result.water_level) == False
                ]
                self.result["station_id"] = str(station.iloc[0]["id"])

                self.result.water_level = self.result.water_level / 100
                self.result.meteorological_tide = self.result.meteorological_tide / 100

                self.result.date_time = self.result.date_time + timedelta(hours=3)
                if len(self.result) > 0:
                    self.db.feed_bd(table="data_stations", df=self.result)

        quit_driver(self.driver)


if __name__ == "__main__":
    EpagriTide().get()
