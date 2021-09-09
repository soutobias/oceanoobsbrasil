import os

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime as dt
import time
import pandas as pd



driver = webdriver.Firefox(executable_path ='/home/remobs/Bots/geckodriver')


site_1 = os.environ["SITE_EBN"]
user = os.environ["USER_EBN"]
pwd = os.environ["PWD_EBN"]


driver.get(site_1)

login = driver.find_element_by_id("login")
login.send_keys(user)

psw = driver.find_element_by_id("senha")
psw.send_keys(pwd)

log_btn = driver.find_element_by_id("entrar")
log_btn.click()

menu_report = driver.find_element_by_id("menu_623")
menu_report.click()

time.sleep(4)
xpath_data = "//button[@class='btn btn-info'][@title='Dados']"
data_btn = driver.find_element_by_xpath(xpath_data)
data_btn.click()

id_table = 'tabela_lista'
tbody = driver.find_element_by_id(id_table)
tr = tbody.find_elements_by_tag_name('tr')

tide_df = pd.DataFrame(columns=['date_time', 'level'])

# date_time_stop
stop_datetime = dt.strptime('25/06/2021', "%d/%m/%Y")

len_tr = len(tr)

while True:
    for row,table_row in enumerate(tr):
        values = table_row.find_elements_by_tag_name('td')
        if values == []:
            continue
        date = values[0].text
        tide_level = values[1].text

        date_time = dt.strptime(date, "%d/%m/%Y %H:%M:%S")


        if date_time < stop_datetime:
            break

        row = {'date_time':date_time, 'level':tide_level}

        tide_df = tide_df.append(row, ignore_index = True)


        print(date_time, tide_level)