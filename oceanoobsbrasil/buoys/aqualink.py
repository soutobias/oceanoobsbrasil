

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

class AqualinkBuoy():

  def __init__(self,
    args=["-headless", "--no-sandbox", "--disable-dev-shm-usage"],
    preferences=[],
    equip='buoy'):


    self.options = Options()
    self.args = args
    self.preferences = preferences
    self.options = def_args_prefs(self.options, self.args, self.preferences)
    self.driver = webdriver.Chrome(options=self.options)

    self.db = GetData()
    self.equip = equip
    self.stations = self.db.get(table='stations', institution=['=', 'aqualink'], data_type=['=', self.equip])

    self.url='https://aqualink.org/sites/'

  def get(self):
    for index, station in self.stations.iterrows():
      url=f"{self.url}{station.url}"
      self.driver.get(url)
      time.sleep(10)
      soup=BeautifulSoup(self.driver.page_source, 'html.parser')
      l = soup.find_all(attrs={'class': 'MuiCard-root'})[3]
      text = l.text
      print(text)
      text = text.replace('WINDSPEED', '')
      text = text.replace('km/hDIRECTION', ',')
      text = text.replace('°WAVESHEIGHT', ',')
      text = text.replace('mPERIOD', ',')
      text = text.replace('sDIRECTION', ',')
      text = text.replace('°Last data received ', ',')
      text = text.replace(' ',',')
      text = text.split(',')[0:7]
      print(text)
      if text[-1] == 'min.':
        columns = ['wspd', 'wdir', 'swvht', 'tp', 'wvdir']
        values = np.array(text[0:5])
        self.result = pd.DataFrame(values).T
        self.result.columns = columns
        self.result.wspd = pd.to_numeric(self.result.wspd) * 0.539957
        l = soup.find_all(attrs={'class': 'MuiCard-root'})[1].text
        l = l.replace('BUOY OBSERVATIONTEMP AT 1m', '')
        sst = l.split('°')[0]
        self.result['sst'] = sst
        self.result['date_time'] = datetime.utcnow().strftime("%Y-%m-%d %H:00:00")
        self.result['station_id'] = str(station['id'])
        print(self.result)
        self.db.feed_bd(table='data_stations', df=self.result)
    quit_driver(self.driver)


if __name__ == '__main__':
    AqualinkBuoy().get()

