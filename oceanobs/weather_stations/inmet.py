import datetime
import json
import os
import time
import urllib.request
import warnings
from datetime import datetime, timedelta
from itertools import cycle

import chromedriver_binary
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from oceanoobsbrasil.db import GetData
from oceanoobsbrasil.utils import *

warnings.filterwarnings("ignore")


class Inmet:
    def __init__(
        self,
        start_date=(datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d"),
        end_date=(datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        args=[
            "-headless",
            "--start-maximized",
            "--disable-gpu",
            "--no-sandbox",
            "--log-level=3",
            "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.100 Safari/537.36",
        ],
        preferences={
            "dom.disable_beforeunload": True,
            "browser.tabs.warnOnClose": False,
        },
        api="https://apitempo.inmet.gov.br",
    ):
        # options.setExperimentalOption("excludeSwitches", Collections.singletonList("enable-automation"));
        #     options.setExperimentalOption("useAutomationExtension", false);

        self.db = GetData()
        self.api = "https://tempo.inmet.gov.br/TabelaEstacoes/"
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(table="stations", institution=["=", "inmet"])

        self.options = Options()
        self.args = args
        self.preferences = preferences

        self.options = def_args_prefs(self.options, self.args, self.preferences)

    def get(self, save_bd=True):
        for index, station in self.stations.iterrows():
            print(station.url)

            url = f"{self.api}{station.url}"
            try:
                print(url)
                self.driver = webdriver.Chrome(options=self.options)
                self.driver.get(url)
                print("XXXXXXXXXXXX")
                time.sleep(8)
                print("XXXXXXXXXXXX")
                df = pd.read_html(self.driver.page_source, decimal=",", thousands=".")

                if df[0].isna().sum().sum() != 408:
                    df = df[0].iloc[:, [0, 1, 2, 11, 14, 15, 16]]
                    df.columns = [
                        "date",
                        "hour",
                        "atmp",
                        "pres",
                        "wspd",
                        "wdir",
                        "gust",
                    ]
                    df["hour"] = (
                        (df["hour"] / 100).astype(int).astype("str").str.zfill(2)
                    )
                    df["date_time"] = pd.to_datetime(
                        df["date"] + df["hour"], format="%d/%m/%Y%H"
                    )

                    df.drop(columns=["date", "hour"], inplace=True)

                    self.result = df.replace(
                        to_replace=["None", "NULL", " ", ""], value=np.nan
                    )

                    self.result.date_time = self.result.date_time + timedelta(hours=3)
                    self.result = self.result[self.result.date_time < datetime.utcnow()]

                    self.result["gust"] = pd.to_numeric(
                        self.result["gust"], errors="coerce"
                    )
                    self.result.gust[self.result.gust.notnull()] = (
                        self.result.gust[self.result.gust.notnull()] * 1.94384
                    ).round(decimals=1)
                    self.result["wspd"] = pd.to_numeric(
                        self.result["wspd"], errors="coerce"
                    )
                    self.result.wspd[self.result.wspd.notnull()] = (
                        self.result.wspd[self.result.wspd.notnull()] * 1.94384
                    ).round(decimals=1)
                    print(self.result)
                    if save_bd:
                        self.result["station_id"] = str(station["id"])
                        self.db.feed_bd(table="data_stations", df=self.result)
                    else:
                        return self.result
                else:
                    print("Nao ha dados para essa estação")
            except Exception as e:
                print(e)
                print("Nao ha dados para essa estação")
            try:
                quit_driver(self.driver)
            except:
                print("driver já finalizado")

    def get_old(self, save_bd=True):
        for index, station in self.stations.iterrows():
            print(station.url)

            url = f"{self.api}/estacao/{self.start_date}/{self.end_date}/{station.url}"
            try:
                response = requests.get(url, timeout=30)
                df = pd.DataFrame(response)
                if response.status_code == 200:
                    df = pd.DataFrame(response.json())
                    df = df[
                        [
                            "PRE_INS",
                            "VEN_DIR",
                            "DT_MEDICAO",
                            "VEN_VEL",
                            "VEN_RAJ",
                            "TEM_INS",
                            "HR_MEDICAO",
                        ]
                    ]
                    df.columns = [
                        "pres",
                        "wdir",
                        "date",
                        "wspd",
                        "gust",
                        "atmp",
                        "hour",
                    ]
                    df["date_time"] = pd.to_datetime(
                        df["date"] + df["hour"], format="%Y-%m-%d%H%M"
                    )
                    df.drop(columns=["date", "hour"], inplace=True)
                    df = df[df.date_time < datetime.utcnow()]

                    self.result = df.replace(
                        to_replace=["None", "NULL", " ", ""], value=np.nan
                    )

                    self.result.date_time = self.result.date_time + timedelta(hours=3)

                    self.result["gust"] = pd.to_numeric(
                        self.result["gust"], errors="coerce"
                    )
                    self.result.gust[self.result.gust.notnull()] = (
                        self.result.gust[self.result.gust.notnull()] * 1.94384
                    ).round(decimals=1)
                    self.result["wspd"] = pd.to_numeric(
                        self.result["wspd"], errors="coerce"
                    )
                    self.result.wspd[self.result.wspd.notnull()] = (
                        self.result.wspd[self.result.wspd.notnull()] * 1.94384
                    ).round(decimals=1)

                    if save_bd:
                        self.result["station_id"] = str(station["id"])
                        self.db.feed_bd(table="data_stations", df=self.result)
                    else:
                        return self.result
                else:
                    print("Nao ha dados para essa estação")
            except Exception as e:
                print(e)
                print("Nao ha dados para essa estação")


if __name__ == "__main__":
    Inmet().get(save_bd=True)
