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

class HydroMetIlhaFiscal():
    
    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='tide'):
        
        
        self.options = Options()
        self.args = args
        self.preferences = preferences
        #self.def_args_prefs()
        self.driver = webdriver.Chrome(options=self.options)
        
        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(table='stations', institution=['=', 'HydroMet'], data_type=['=', self.equip])
        self.url = os.getenv("SITE_ILHAFISCAL")
        self.user = os.getenv("USER_ILHAFISCAL")
        self.pwd = os.getenv("PSW_ILHAFISCAL")
                 


    def get(self):

       


        site = self.url
        user = self.user
        pwd = self.pwd 
        driver = self.driver



        driver.get(site)
        time.sleep(4)


        driver.find_element_by_name("Login").click()
        elem = driver.find_element_by_name("userName")

        elem.send_keys(user)

        elem = driver.find_element_by_name("password")
        elem.send_keys(pwd)

        # Clicando no botao.

        login_bt = driver.find_element_by_xpath("//button[@type='submit']")
        login_bt.click()
        time.sleep(6)

        # Logged

        data_report_link = 'http://www.hydrometcloud.com/hydrometcloud/jsp/CustomReport/CustomReports.jsp?menu=CustomReports'

        driver.get(data_report_link)

        time.sleep(5)
        # Click on checkbox DELFOS_MARITIMA
        box_delfos = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/span/span[1]")
        box_delfos.click()

        time.sleep(4)
        box_ilha_fiscal = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/span/span[1]")
        box_ilha_fiscal.click()

        time.sleep(4)
        kalesto = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/ul/li[1]/span/span[2]")
        kalesto.click()

        custom_time = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[2]/div[1]/label")
        custom_time.click()

        initial_time_field = driver.find_element_by_xpath("//*[@id='fromFld']")
        last_time_field = driver.find_element_by_xpath("//*[@id='toFld']")
        
        # last data on db 
    
        last_time_db = self.db.get("data_stations", last = self.stations.id[0])
        last_time = last_time_db['date_time'][0] + timedelta(minutes=5)
        last_time_str = dt.strftime(last_time, "%Y-%m-%d %H:%M")

        initial_time_field.send_keys(last_time_str)

        now = dt.now().strftime("%Y-%m-%d %H:%M")
        last_time_field.send_keys(now)
        
        #
        plot_button = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[3]/ul/li[1]/button")
        plot_button.click()


        time.sleep(4)
        # DownloadButton
        menu_plot = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[4]/div/button")
        menu_plot.click()


        data_table_el = driver.find_element_by_xpath('/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[3]/div/div/div[9]')
        data_table_el.click()

        tbody = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[3]/table/tbody")

        tr = tbody.find_elements_by_tag_name('tr')

        df_tide = pd.DataFrame(columns=["date_time", "water_level"])

        for table_row in tr:
            th = table_row.find_elements_by_tag_name('th')[0].text
            td = table_row.find_elements_by_tag_name('td')[0].text
            
            #print(th, td)
            
            level = float(td)   

            tide_obs = {"date_time":th,"water_level":level}

            df_tide = df_tide.append(tide_obs, ignore_index=True)

        print("All data fetched.")
        df_tide['station_id'] = self.stations.id[0]
        
        self.db = GetData()
        print("Inserting on database.")
        self.db.post(table='data_stations', df=df_tide)
        


    def quit_driver(self):
        driver_process = psutil.Process(self.driver.service.process.pid)
        #driver.quit()

        if driver_process.is_running():
            print ("driver is running")

            firefox_process = driver_process.children()
            if firefox_process:
                firefox_process = firefox_process[0]

                if firefox_process.is_running():
                    print("Chrome is still running, we can quit")
                    self.driver.quit()
                else:
                    print("Chrome is dead, can't quit. Let's kill the driver")
                    firefox_process.kill()
            else:
                print("driver has died")
