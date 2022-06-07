
import time
import datetime
import urllib.request, json
import requests

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from oceanoobsbrasil.db import GetData


class RicoSurf():

    def __init__(self,
        equip='visual'):

        self.db = GetData()
        self.equip = equip
        self.url = 'https://ricosurf.com.br/boletim-das-ondas/rio-janeiro'
        self.stations = self.db.get(table='stations', institution=['=', 'ricosurf'], data_type=['=', self.equip])

    def get(self):

        response = requests.get(self.url)

        soup = BeautifulSoup(response.text,'html.parser')

        self.beaches = self.beaches_with_data(soup)

        for index, station in self.stations.iterrows():
            print(station['name'])
            if self.beach_has_data(station):
                print('Data available')
                response = requests.get(station["url"])

                soup = BeautifulSoup(response.text,'html.parser')

                l = soup.find("div", {"class": "h5 text-primary margin-xxs-bottom"}).get_text(strip=True).replace(",", ".")
                swvht = float(l[0:-1])

                l = soup.find_all('div', attrs={'class': 'h5 no-margin text-primary'})
                tp = l[0].get_text(strip=True).replace(",", ".")
                tp = float(tp[0:-1])
                sst = l[1].get_text(strip=True)
                sst = float(sst[0:-2])
                wvdir = soup.find("div", {"class": "small line-height-xs"}).get_text(strip=True).lower()
                if wvdir == "norte":
                    wvdir = 0
                if wvdir == "norte-nordeste" or wvdir == "norte nordeste":
                    wvdir = 22
                if wvdir == "nordeste":
                    wvdir = 45
                if wvdir == "nordeste-leste" or wvdir == "nordeste leste" or wvdir == "leste nordeste" or wvdir == "leste-nordeste":
                    wvdir = 45 + 22
                if wvdir == "leste":
                    wvdir = 90
                if wvdir == "sudeste-leste" or wvdir == "sudeste leste" or wvdir == "leste sudeste" or wvdir == "leste sudeste":
                    wvdir = 90 + 22
                if wvdir == "sudeste":
                    wvdir = 90 + 45
                if wvdir == "sul-sudeste" or wvdir == "sul sudeste" or wvdir == "sudeste sul" or wvdir == "sudeste-sul":
                    wvdir = 90+45+22
                if wvdir == "sul":
                    wvdir = 180
                if wvdir == "sul-sudoeste" or wvdir == "sul sudoeste" or wvdir == "sudoeste-sul" or wvdir == "sudoeste sul":
                    wvdir = 180 + 22
                if wvdir == "sudoeste":
                    wvdir = 180 + 45
                if wvdir == "sudoeste-oeste" or wvdir == "sudoeste oeste" or wvdir == "oeste-sudoeste" or wvdir == "oeste sudoeste":
                    wvdir = 180 + 45 + 22
                if wvdir == "oeste":
                    wvdir = 270
                if wvdir == "noroeste-oeste" or wvdir == "noroeste oeste" or wvdir == "oeste-noroeste" or wvdir == "oeste noroeste":
                    wvdir = 270 + 22
                if wvdir == "noroeste":
                    wvdir = 270 + 45
                if wvdir == "noroeste-norte" or wvdir == "noroeste norte" or wvdir == "norte-noroeste" or wvdir == "norte noroeste":
                    wvdir = 270 + 45 + 22
                if wvdir == 'não informado':
                    wvdir = np.nan

                date_time = datetime.now()
                date_time = date_time.replace(minute=0, second=0, microsecond=0)

                values = np.array([date_time, swvht, tp, sst, wvdir])
                columns = ['date_time', 'swvht', 'tp', 'sst', 'wvdir']

                self.result = pd.DataFrame(values).T
                self.result.columns = columns
                self.result = self.result.replace(to_replace =['None', 'NULL', ' ', ''], value =np.nan)

                self.result['station_id'] = str(station['id'])
                self.db.feed_bd(table='data_stations', df=self.result)
                print('dados alimentados')
            else:
                print('No data for this station')


    def beach_has_data(self, station):
        if station['name'] in self.beaches:
            return True
        return False

    def beaches_with_data(self, soup):
        l = soup.find_all('li', attrs={'data-toggle': 'popover'})
        beaches = []
        for beach in l:
            if beach['data-content'][-10:-6] != 'zado':
                beaches.append(beach.text.strip()[1:])
        return beaches

if __name__ == '__main__':
    RicoSurf().get()
