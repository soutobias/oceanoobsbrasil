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


class PEBuoy():

    load_dotenv()

    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='buoy'):


        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.def_args_prefs()
        self.driver = webdriver.Chrome(options=self.options)

        self.db = GetData()
        self.equip = equip
        self.stations = self.bd.get(table='stations', institution=['=', 'hidromares'], name=['=', 'suape'], data_type=['=', self.equip]).iloc[0]

        self.url=os.getenv('PE_URL')

    def get(self):

        self.driver.get(self.url)
        time.sleep(10)
        # wait = WebDriverWait(self.driver, 15)
        # wait.until(ec.visibility_of_element_located((By.XPATH, "//div[@id='Box01_1631']")))

        mwd = int(self.driver.find_element_by_xpath("//div[@id='Box01_1631']").text)
        hm0 = float(self.driver.find_element_by_xpath("//div[@id='Box01_718']").text)
        seapeakdir = int(self.driver.find_element_by_xpath("//div[@id='Box04_1633']").text)
        seahm0= float(self.driver.find_element_by_xpath("//div[@id='Box04_1627']").text)
        swellpeakdir = int(self.driver.find_element_by_xpath("//div[@id='Box07_1634']").text)
        swellhm0 = float(self.driver.find_element_by_xpath("//div[@id='Box07_1624']").text)

        date_time = self.driver.find_element_by_xpath("//*[contains(text(), 'Latest data')]").text
        date_time = datetime.strptime(date_time[13:], '%Y-%m-%d %H:%M')

        self.driver.find_element_by_xpath("//a[contains(text(),'PÍER')]").click()
        time.sleep(10)

        # wait.until(ec.visibility_of_element_located((By.XPATH, "//div[@id='Box01_arrow']")))

        soup=BeautifulSoup(self.driver.page_source, 'html.parser')

        l=soup.find_all(attrs={'id': 'Box01_arrow'})
        x=l[0].path.attrs
        x2=x['transform']

        x1=re.findall("[+-]?\d+\.\d+",x2)
        (intens,direc)=uv2intdir(float(x1[0]),float(x1[1]))
        wdir = round(direc)

        l=soup.find_all(attrs={'id': 'Box01_689'})
        wspd =float(l[0].text)*0.514444
        wspd = round(wspd, 2)

        l=soup.find_all(attrs={'id': 'Box01_690'})
        gust=float(l[0].text)*0.514444
        gust = round(gust, 2)

        values = np.array([date_time, mwd, hm0, seapeakdir, seahm0, swellpeakdir, swellhm0, wspd, gust, wdir])
        columns = ['date_time', 'wvdir', 'swvht', 'wvdir_sea', 'swvht_sea', 'wvdir_swell', 'swvht_swell', 'wspd', 'gust', 'wdir']
        self.result = pd.DataFrame(values).T
        self.result.columns = columns

        self.result['station_id'] = str(self.stations['id'])

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

