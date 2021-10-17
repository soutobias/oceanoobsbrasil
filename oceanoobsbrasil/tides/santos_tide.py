import os
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
import pandas as pd

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *

import chromedriver_binary

from dotenv import load_dotenv

class TideSantos():
    
    load_dotenv()

    def __init__(self,
        args=["-headless", "--no-sandbox", "--disable-dev-shm-usage"],
        preferences=[]):

        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.options = def_args_prefs(self.options, self.args, self.preferences)
        self.driver = webdriver.Chrome(options=self.options)

        self.db = GetData()
        self.stations = self.db.get(table='stations', institution=['=', 'SantosPilot'])

        self.url = os.getenv("SITE_SANTOS")
        self.user = os.getenv("USER_SANTOS")
        self.pwd = os.getenv("PWD_SANTOS")

        
    def get(self):
        
        self.login()

        self.points_of_tide = self.driver.find_elements_by_xpath("//img[@alt='Ver Marégrafo']")
        xpath_close_box = '//*[@id="fancybox-close"]'

        for point in self.points_of_tide:
            point.click()
            time.sleep(3)

            self.driver.switch_to.frame("fancybox-frame")

            name = self.driver.find_element_by_class_name("name").text.lower()
            print(name)
            station = self.stations[self.stations.url == name]

            df = pd.read_html(self.driver.page_source)[1]
            df['HORA'] = pd.to_datetime(datetime.utcnow().strftime("%Y-%m-%d") + df['HORA'], format='%Y-%m-%d%H:%M')
            df['HORA'] = df['HORA'] + timedelta(hours=3)

            df.columns = ['date_time', 'water_level_pred', 'water_level']
            df = df[df.date_time < datetime.utcnow()]

            df['meteorological_tide'] = df['water_level'] - df['water_level_pred']

            df.drop(columns='water_level_pred', inplace=True)

            self.result = df.replace(to_replace =['None', 'NULL', ' ', ''],
                                    value =np.nan)

            self.result['station_id'] = str(station.iloc[0]['id'])

            self.result.date_time = self.result.date_time + timedelta(hours=3)

            self.db.feed_bd(table='data_stations', df=self.result)
            print(name + " ok")
            self.driver.switch_to.default_content()
            self.driver.find_element_by_xpath(xpath_close_box).click()
            time.sleep(2)

        quit_driver(self.driver)

    def login(self):
        self.driver.get(self.url)
        time.sleep(5)

        login_elem = self.driver.find_element_by_xpath('//*[@id="CustomerEmail"]')
        login_elem.send_keys(self.user)

        psw_elem = self.driver.find_element_by_xpath("//*[@id='CustomerPassword']")
        psw_elem.send_keys(self.pwd)


        login_bt = self.driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/form/div[2]/input")
        login_bt.click()
        time.sleep(5)

if __name__ == '__main__':
    TideSantos().get()
