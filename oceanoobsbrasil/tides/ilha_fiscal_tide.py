import os
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from datetime import datetime as dt
from datetime import timedelta
import time
import pandas as pd
import psutil

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *
import chromedriver_binary

from dotenv import load_dotenv


class IlhaFiscal():

    load_dotenv()


    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='tide'):
        
        
        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.options = def_args_prefs(self.options, self.args, self.preferences)
        self.driver = webdriver.Chrome(options=self.options)
        
        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(table='stations', institution=['=', 'HydroMet'], data_type=['=', self.equip]).iloc[0]

        self.url = os.getenv("SITE_ILHAFISCAL")
        self.url_report = os.getenv("SITE_ILHAFISCAL_REPORT")
        self.user = os.getenv("USER_ILHAFISCAL")
        self.pwd = os.getenv("PWD_ILHAFISCAL")
                 
    def get(self):

        self.login()

        self.driver.get(self.url_report)
        time.sleep(8)

        self.driver.find_element_by_class_name('dynatree-checkbox').click()

        self.driver.find_element_by_class_name('data-reports').click()
        time.sleep(6)

        self.driver.find_element_by_id('tab3').click()
        time.sleep(3)


        try:
            df = pd.read_html(self.driver.page_source)[3]
            df.columns = ['date_time', 'water_level', 'elev_1']
            df = df.iloc[3:-1]
            df = df[['date_time', 'water_level']]
            df['date_time'] = pd.to_datetime(df['date_time'], format='%Y-%m-%d %H:%M')

            self.result = df.replace(to_replace =['None', 'NULL', ' ', ''],
                                    value =np.nan)

            self.result['station_id'] = str(self.stations['id'])

            self.result.date_time = self.result.date_time + timedelta(hours=3)

            self.db.feed_bd(table='data_stations', df=self.result)

            quit_driver(self.driver)

        except:
            print('No data for this station')

    def login(self):
        self.driver.get(self.url)
        time.sleep(5)

        self.driver.find_element_by_name("Login").click()

        elem = self.driver.find_element_by_name("userName")
        elem.send_keys(self.user)

        elem = self.driver.find_element_by_name("password")
        elem.send_keys(self.pwd)

        login_bt = self.driver.find_element_by_xpath("//button[@type='submit']")
        login_bt.click()

        time.sleep(5)
