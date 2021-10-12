"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

import pandas as pd
import numpy as np
import re

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
import chromedriver_binary
from bs4 import BeautifulSoup

from datetime import datetime, timedelta
import time

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *

import psutil
import os


class WindGuru():

    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='meteorological_station'):


        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.def_args_prefs()

        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(table='stations', institution=['=', 'windguru'], data_type=['=', self.equip])
        self.url="https://www.windguru.cz/station/"

    def get(self):

        for index, station in self.stations.iterrows():
            print(station['name'])
            self.driver = webdriver.Chrome(options=self.options)
            self.driver.get(f"{self.url}{station['url']}")
            print(f"{self.url}{station['url']}")
            time.sleep(8)


            self.soup=BeautifulSoup(self.driver.page_source, 'html.parser')

            wspd = self.soup.find(attrs={'class': 'wgs_wind_avg_value'}).text
            if wspd == '':
                wspd = None

            wdir = self.soup.find(attrs={'class': 'wgs_wind_dir_numvalue'}).text[:-1]
            if wdir == '':
                wdir = None

            sst = self.soup.find(attrs={'class': 'wgs_temp_value'}).text
            if sst == '':
                sst = None

            l = self.soup.find(attrs={'class': 'wgs_last_time'}).text
            date_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')[:-1]+"0"

            values = np.array([date_time, wspd, wdir, sst])
            columns = ['date_time', 'wspd', 'wdir', 'sst']

            self.result = pd.DataFrame(values).T
            self.result.columns = columns

            self.result['station_id'] = str(station['id'])

            print(self.result)

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
        self.db.post(table='data_stations', df=self.result)


    def quit_driver(self):
        driver_process = psutil.Process(self.driver.service.process.pid)
        #driver.quit()

        if driver_process.is_running():
            print ("driver is running")

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

