import time

import pandas as pd 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime as dt


driver = webdriver.Firefox(executable_path ='/home/remobs/Bots/geckodriver')


site_1 = os.environ["SITE_ILHAFISCAL"]
user = os.environ["USER_ILHAFISCAL"]
pwd = os.environ["PSW_ILHAFISCAL"]



driver.get(site_1)


driver.find_element_by_name("Login").click()
elem = driver.find_element_by_name("userName")

elem.send_keys(user)

elem = driver.find_element_by_name("password")
elem.send_keys(pwd)

# Clicando no botao.

login_bt = driver.find_element_by_xpath("//button[@type='submit']")
login_bt.click()


# Logged

data_report_link = 'http://www.hydrometcloud.com/hydrometcloud/jsp/CustomReport/CustomReports.jsp?menu=CustomReports'

driver.get(data_report_link)

# Click on checkbox DELFOS_MARITIMA
box_delfos = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/span/span[1]")
box_delfos.click()

box_ilha_fiscal = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/span/span[1]")
box_ilha_fiscal.click()


kalesto = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[3]/div/ul/li/ul/li/ul/li[1]/span/span[2]")
kalesto.click()

custom_time = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[2]/div[1]/label")
custom_time.click()

initial_time = driver.find_element_by_xpath("//*[@id='fromFld']")
last_time = driver.find_element_by_xpath("//*[@id='toFld']")

initial_time.send_keys("2021-06-24 00:00")

now = dt.now().strftime("%Y-%m-%d %H:%M")
last_time.send_keys(now)

#
plot_button = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[1]/div[4]/div/div[3]/ul/li[1]/button")
plot_button.click()


time.sleep(4)
# DownloadButton
menu_plot = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[4]/div/button")
menu_plot.click()

# DownloadCSV

#csv_file = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[3]/div/div/div[7]")


data_table_el = driver.find_element_by_xpath('/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[3]/div/div/div[9]')
data_table_el.click()

#table = driver.find_element_by_xpath('//*[@id="highcharts-data-table-0"]')
tbody = driver.find_element_by_xpath("/html/body/section/section/div[1]/div[2]/div[2]/div/div[2]/div[1]/div[1]/div[3]/table/tbody")

tr = tbody.find_elements_by_tag_name('tr')

df_tide = pd.DataFrame(columns=["date_time", "tide"])

for table_row in tr:
    th = table_row.find_elements_by_tag_name('th')[0].text
    td = table_row.find_elements_by_tag_name('td')[0].text

     
    print(th, td)
    
    level = float(td)   

    tide_obs = {"date_time":th,"tide":level}

    df_tide = df_tide.append(tide_obs, ignore_index=True)




driver.quit()
