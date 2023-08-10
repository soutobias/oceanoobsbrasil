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


class EpagriMeteo:
    def __init__(
        self, args=["-headless"], preferences=[], equip="meteorological_station"
    ):
        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.def_args_prefs()
        self.driver = webdriver.Chrome(options=self.options)

        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(
            table="stations", institution=["=", "epagri"], data_type=["=", self.equip]
        )
        self.url = "https://ciram.epagri.sc.gov.br/litoral-online/"

    def get(self):
        self.driver.get(self.url)
        time.sleep(5)

        table_NM = pd.read_html(self.driver.page_source)

        for index, station in self.stations.iterrows():
            self.result = table_NM[index]
            self.result["date_time"] = pd.to_datetime(
                self.result.Topping, format="%d/%m %H:%M"
            ) + pd.offsets.DateOffset(years=120)

            self.result = self.result[["Mare Obser.", "Residual", "date_time"]]
            columns = ["water_level", "meteorological_tide", "date_time"]
            self.result.columns = columns

            self.result = self.result.replace(
                to_replace=["None", "NULL", " ", ""], value=np.nan
            )
            self.result = self.result.loc[np.isnan(self.result.water_level) == False]

            self.result["station_id"] = str(station["id"])

            self.feed_bd()

        self.quit_driver()

    def def_args_prefs(self):
        for arg in self.args:
            if type(arg) == list:
                self.options.add_argument(arg[0], arg[1])
            else:
                self.options.add_argument(arg)

        for preference in self.preferences:
            if type(preference) == list:
                self.options.set_preference(preference[0], preference[1])
            else:
                self.options.set_preference(preference[0])

    def feed_bd(self):
        self.db.post(table="data_stations", df=self.result)

    def quit_driver(self):
        driver_process = psutil.Process(self.driver.service.process.pid)
        # driver.quit()

        if driver_process.is_running():
            print("driver is running")

            firefox_process = driver_process.children()
            if firefox_process:
                firefox_process = firefox_process[0]

                if firefox_process.is_running():
                    print("Firefox is still running, we can quit")
                    self.driver.quit()
                else:
                    print("Firefox is dead, can't quit. Let's kill the driver")
                    firefox_process.kill()
            else:
                print("driver has died")
