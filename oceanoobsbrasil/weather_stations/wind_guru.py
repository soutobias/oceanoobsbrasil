
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


class WindGuru():

    def __init__(self,
        args=["-headless", "--no-sandbox", "--disable-dev-shm-usage"],
        preferences=[],
        equip='meteorological_station'):

        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.options = def_args_prefs(self.options, self.args, self.preferences)

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

            atmp = self.soup.find(attrs={'class': 'wgs_temp_value'}).text
            if atmp == '':
                atmp = None

            l = self.soup.find(attrs={'class': 'wgs_last_time'}).text
            date_time = datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')[:-1]+"0"

            values = np.array([date_time, wspd, wdir, atmp])
            columns = ['date_time', 'wspd', 'wdir', 'atmp']

            self.result = pd.DataFrame(values).T
            self.result.columns = columns

            self.result['station_id'] = str(station['id'])
            print(self.result)
            self.db.feed_bd(table='data_stations', df=self.result)

            quit_driver(self.driver)

if __name__ == '__main__':
    WindGuru().get()
