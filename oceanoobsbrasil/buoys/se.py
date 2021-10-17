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
from dotenv import load_dotenv


class SEBuoy():

    load_dotenv()

    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='buoy'):

        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.options = def_args_prefs(self.options, self.args, self.preferences)
        self.driver = webdriver.Chrome(options=self.options)

        self.bd = GetData()
        self.equip = equip
        self.stations = self.bd.get(table='stations', institution=['=', 'hidromares'], name=['=', 'celse'], data_type=['=', self.equip]).iloc[0]

        self.url=os.getenv('SE_URL')


    def get(self):

        self.driver.get(self.url)
        self.logging()

        number = 0  # first frame
        self.driver.switch_to.frame(number)
        self.soup=BeautifulSoup(self.driver.page_source, 'lxml')

        mwd = self.get_data("Box02_1560")
        hm0 = self.get_data("Box02_1544")
        wspd = self.get_data("Box01_1555")
        gust = self.get_data("Box01_1564")

        if wspd!=None:
            wspd=round(wspd*0.514444, 2)
        if gust!=None:
            gust=round(gust*0.514444, 2)


        data=self.soup.find("div", {"id": "Box11_h0"}).get_text(strip=True)
        hour = int(data[0:2])
        minute = int(data[3:5])

        date_time = datetime.utcnow() - timedelta(hours=3)
        date_time = date_time.replace(hour=hour)
        date_time = date_time.replace(minute=minute)
        date_time = date_time.strftime("%Y-%m-%d %H:%M")

        values = np.array([date_time, hm0, mwd, wspd, gust])
        columns = ['date_time', 'swvht', 'wvdir', 'wspd', 'gust']

        self.result = pd.DataFrame(values).T
        self.result.columns = columns
        self.result['station_id'] = str(self.stations['id'])

        self.db.feed_bd(table='data_stations', df=self.result)

        quit_driver(self.driver)


    def get_data(self, attrs):
        try:
            value=float(self.soup.find("div", {"id": attrs}).get_text(strip=True))
        except:
            value = np.nan
        return value

    def logging(self):
        time.sleep(10)
        self.driver.find_element_by_css_selector("#id_username").send_keys(os.getenv('SE_USER'))
        self.driver.find_element_by_css_selector("#id_password").send_keys(os.getenv('SE_PWD'))
        self.driver.find_element_by_css_selector("#wp-submit").click()
        time.sleep(10)

