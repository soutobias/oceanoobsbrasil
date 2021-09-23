from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException,ElementNotInteractableException

from datetime import datetime as dt
import time
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup as bs
import lxml


from db_mare import db_conn



class Tide_Santos():
    
    def __init__(self,
        args=["-headless"],
        preferences=[],
        equip='tide'):
        
        
        self.options = Options()
        self.args = args
        self.preferences = preferences
        self.def_args_prefs()
        self.driver = webdriver.Chrome(options=self.options),
        
        self.db = GetData()
        self.equip = equip
        self.stations = self.db.get(table='stations', institution=['=', 'epagri'], data_type=['=', self.equip])
        self.url = os.getenv("SITE_SANTOS")
        self.user = os.getenv("USER_SANTOS")
        self.pwd = os.getenv("PSW_SANTOS")
        
        
    def get(self):
        

        driver = webdriver.Firefox(executable_path ='/home/remobs/Bots/geckodriver')


        site = self.url
        user = self.user
        pwd = self.pwd 
        driver = self.driver


        driver.get(site)

        login_elem = driver.find_element_by_xpath('//*[@id="CustomerEmail"]')
        login_elem.send_keys(user)

        psw_elem = driver.find_element_by_xpath("//*[@id='CustomerPassword']")
        psw_elem.send_keys(pwd)

        login_bt = driver.find_element_by_xpath("/html/body/div[1]/div/div[2]/div[3]/form/div[2]/input")
        login_bt.click()




        xpath_zoom_ilha_palmas = "/html/body/div[1]/div/div[2]/div[3]/div[2]/div[2]/div[4]/a/img"
        xpath_praticagem = "/html/body/div[1]/div/div[2]/div[3]/div[2]/div[4]/div[4]/a/img"
        xpath_capitania = "/html/body/div[1]/div/div[2]/div[3]/div[2]/div[6]/div[4]/a/img"
        xpath_ilha_barnabe = "/html/body/div[1]/div/div[2]/div[3]/div[2]/div[8]/div[4]/a/img"
        xpath_tiplam = "/html/body/div[1]/div/div[2]/div[3]/div[2]/div[10]/div[4]/a/img"

        points_of_tide = [xpath_zoom_ilha_palmas, xpath_praticagem, xpath_capitania, xpath_ilha_barnabe, xpath_tiplam]

        points_of_tide = {"Ilha das Palmas - Santos":xpath_zoom_ilha_palmas,
                            "Praticagem - Santos": xpath_praticagem,
                            "Capitania - Santos": xpath_capitania,
                            "Ilha Barnabe - Santos": xpath_ilha_barnabe,
                            "Tiplam - Santos":xpath_tiplam}

        xpath_close_box = '//*[@id="fancybox-close"]'



        for station in points_of_tide:

            point = points_of_tide[station]

            data_tide = pd.DataFrame(columns=['HORA','MARE_PREVISTA', 'MARE_OBSERVADA'])

            try:
                pt_tide = driver.find_element_by_xpath(point)
                pt_tide.click()
            except ElementNotInteractableException:
                print(station)
                print("Station not available.")
                continue

        #    pt_tide = driver.find_element_by_xpath(point)
        #    pt_tide.click()

            time.sleep(3)
            driver.switch_to.frame("fancybox-frame")


            get_date_data = driver.find_element_by_xpath("/html/body/div[3]/div[2]/div/div[5]/p[2]")
            date_tide = get_date_data.text

            date_time_str = date_tide[14:24]
            date_dt = dt.strptime(date_time_str, "%d/%m/%Y")



            print(get_date_data.text)
            data_table = driver.find_element_by_xpath("/html/body/div[3]/div[3]/div/table/tbody")

            page_data = driver.page_source.encode("utf-8")
            xml_page = bs(page_data, 'lxml')
            data_table_xml = xml_page.find_all('tbody')[-1]

            table_rows = data_table_xml.find_all('tr')

            for row in table_rows:
                values = row.find_all('td')
                if values == []:
                    continue

                hour = values[0].text
                forecast_tide = values[1].text
                observed_tide = values[2].text

                if observed_tide == "\xa0":
                    observed_tide = np.nan

                row_df = {'HORA':hour, 'MARE_PREVISTA':forecast_tide, 'MARE_OBSERVADA':observed_tide}

                data_tide = data_tide.append(row_df, ignore_index=True)

            print(f"Data for {station} station")
            print(data_tide)

            # Concat date and hour
            data_tide['DATE'] = date_time_str

            data_tide['date_time'] = data_tide['DATE'] + " " + data_tide['HORA'] 

            data_tide = data_tide[["date_time", "MARE_OBSERVADA"]]
            data_tide.columns = ['date_time', 'water_level']
            



            data_tide.dropna(axis=0, inplace=True)
            data_tide['water_level'] = data_tide['water_level'].astype(float)
            data_tide['date_time'] = pd.to_datetime(data_tide['date_time'])
            print(data_tide)


            # database 
            conn = db_conn()

            station_id = conn.get_station_id(station).values[0][0]

            data_tide['station_id'] = station_id

            # last_data on db

            last_date = conn.get_last_data_tide(station_id)

            if last_date.iloc[0][0] == None:
                print("Inserting data on db")
                conn.insert_tide(data_tide)
            elif last_date.iloc[0][0] != None:
                data_tide = data_tide[data_tide['date_time']>last_date.iloc[0].values[0]]
                if not data_tide.empty:
                    print("Inserting data on db")
                    conn.insert_tide(data_tide)



            driver.switch_to.default_content()
            cls_box = driver.find_element_by_xpath(xpath_close_box)
            cls_box.click()
            time.sleep(2)
