
import time
import datetime
import urllib.request, json
import requests

import re

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from oceanoobsbrasil.db import GetData


class WeatherWarning():

    def __init__(self):

        self.db = GetData()
        self.url = 'https://www.marinha.mil.br/chm/dados-do-smm-avisos-de-mau-tempo'
        self.regions = ['ALFA', 'BRAVO', 'CHARLIE',
                        'DELTA', 'ECHO', 'FOXTROT',
                        'GOLF', 'HOTEL', 'SUL', 'NORTE']

    def get(self):
        response = requests.get(self.url, verify = False)
        soup = BeautifulSoup(response.text,'html.parser')

        all = soup.find("div",  {"class": "region region-content"})
        self.all = all
        ps = all.find_all("p")


        idxs= []
        regions = []
        for i in range(len(ps)):
            r = ps[i].find("span", {'style': "color:#ff0000;"})
            r1 = ps[i].find("span", {'style': "color:#FF0000;"})
            if r1:
                r = r1
            if r:
                r1 = r
                for rr in self.regions:
                    if rr in r.text:
                        regions.append(rr)
                        idxs.append(i)
                        break
        idxs.append(len(ps)-1)
        idx = []
        for i in range(len(idxs)-1):
            idx.append((idxs[i], idxs[i+1]))

        self.params = []
        for index, region in enumerate(regions):
            for i in range(idx[index][0]+1,idx[index][1]):
                r = ps[i].strong
                if r:
                    param = {}
                    hour = (datetime.utcnow().hour//6)*6
                    date_time = datetime.utcnow().replace(hour=hour)
                    
                    param['date_time'] = date_time.strftime(format=f'%Y-%m-%d %H:01:00')
                    param['region'] = region
                    param['warning_number'] = r.text.strip()
                    param['warning_number'] = re.findall('[0-9]+/[0-9]+', param['warning_number'])[0]
                    try:
                        try:
                            all = ps[i].text.strip()
                            all = all.replace('\t', '').split('\n')
                            param['warning_type'] = all[1].replace('AVISO DE', '').strip()
                            param['start_date'] = all[2].replace('EMITIDO ÀS', '').strip()
                            param['description'] = all[3].strip()
                            param['end_date'] = all[4].replace('VÁLIDO ATÉ', '').replace('.', '').strip()
                            param['institution'] = 'CHM'
                        except:
                            i = i+1
                            all = ps[i].text.strip()
                            all = all.replace('\t', '').split('\n')
                            param['warning_type'] = all[0].replace('AVISO DE', '').strip()
                            param['start_date'] = all[1].replace('EMITIDO ÀS', '').strip()
                            param['description'] = all[2].strip()
                            param['end_date'] = all[3].replace('VÁLIDO ATÉ', '').replace('.', '').strip()
                        param['institution'] = 'CHM'
                        self.params.append(param)
                    except:
                        continue

        self.result = pd.DataFrame(self.params)
        print(self.result.region.unique())
        self.db.feed_bd(table='warnings', df=self.result)
        print('ok')
        # print('dados alimentados')
        #     else:
        #         print('No data for this station')

if __name__ == '__main__':
    CleanBeach().get()
