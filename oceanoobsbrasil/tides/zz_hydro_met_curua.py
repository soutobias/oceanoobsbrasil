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
import chromedriver_binary

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *

from dotenv import load_dotenv



class HydroMetCurua():
    
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
        self.stations = self.db.get(table='stations', institution=['=', 'epagri'], data_type=['=', self.equip])
        self.url = os.getenv("SITE_CURUA")
        self.user = os.getenv("USER_CURUA")
        self.pwd = os.getenv("PWD_CURUA")
        
        
    def get(self):


        self.driver.get(self.url)


        self.driver.find_element_by_name("Login").click()
        elem = self.driver.find_element_by_name("userName")

        elem.send_keys(self.user)

        elem = self.driver.find_element_by_name("password")
        elem.send_keys(self.pwd)

        # Clicando no botao.

        login_bt = self.driver.find_element_by_xpath("//button[@type='submit']")
        login_bt.click()


        # Logged

        data_report_link = 'http://www.hydrometcloud.com/hydrometcloud/jsp/CustomReport/CustomReports.jsp?menu=CustomReports'

        self.driver.get(data_report_link)

        # Click on checkbox DELFOS_MARITIMA
        box_delfos = self.driverself.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/span/span[1]")
        box_delfos.click()

        box_ilha_fiscal = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/span/span[1]")
        box_ilha_fiscal.click()


        kalesto = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/ul/li[1]/span/span[2]")
        kalesto.click()

        custom_time = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[2]/div[1]/label")
        custom_time.click()

        initial_time = self.driver.find_element_by_xpath("//*[@id='fromFld']")
        last_time = self.driver.find_element_by_xpath("//*[@id='toFld']")

        initial_time.send_keys("2021-01-01 00:00")

        now = dt.now().strftime("%Y-%m-%d %H:%M")
        last_time.send_keys(now)

        #
        plot_button = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[3]/ul/li[1]/button")
        plot_button.click()


        time.sleep(4)
        # DownloadButton
        menu_plot = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[4]/div/button")
        menu_plot.click()


        data_table_el = self.driver.find_element_by_xpath('/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[3]/div/div/div[9]')
        data_table_el.click()

        tbody = self.driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[3]/table/tbody")

        tr = tbody.find_elements_by_tag_name('tr')

        for table_row in tr:
            th = table_row.find_elements_by_tag_name('th')[0].text
            td = table_row.find_elements_by_tag_name('td')[0].text
            print(th, td)
            
