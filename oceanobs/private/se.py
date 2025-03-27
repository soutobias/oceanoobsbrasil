"""Class to get data from the Brazilian buoys in Sergipe"""
import json
import os
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
import geopandas as gpd
from selenium import webdriver

from oceanobs.oceanobs import Oceanobs
from oceanobs.utils import quit_driver
load_dotenv()

class SEBuoy(Oceanobs):
    """Get data from Sergipe buoys"""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = os.getenv("SE_URL")

    def get_stations(self):


        file_path = os.path.join(os.path.dirname(__file__), "../data/buoy_pe.json")

        with open(file_path, "r") as file:
            stations = json.load(file)

        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)
        return stations

    def get_data(self,
                 station,
                 add_columns: list = None) -> pd.DataFrame:
        """ Get data from a station

        Parameters
        ----------
        station : dict
            The station information

        Returns
        -------
        tuple
            The data and the error message
        """
        if not add_columns:
            add_columns = ["name"]

        driver = self.create_driver()
        try:
            driver.get(self.base_url)
            driver = self.logging(driver)
        except Exception as e:
            quit_driver(driver)
            return None, str(e)

        driver.get(self.base_url)
        time.sleep(10)

        number = 0
        driver.switch_to.frame(number)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        dfs = pd.read_html(str(soup))
        data = None
        for df in dfs:
            if "Channels" in df.columns:
                data = df
                break
        if data is None:
            error = f"No data found: {station['name']}"
            return None, error
        if "Channels" not in data.columns:
            error = f"No data found: {station['name']}"
            return None, error
        data = data.set_index("Channels").T
        data = data.iloc[[0]]
        data = self.rename_columns(data)
        data = self._prepare_data(data)
        if add_columns:
            if "id" in add_columns:
                data["station_id"] = station["id"]

        return data, None

    def rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename columns

        Parameters
        ----------
        data : pd.DataFrame
            The data

        Returns
        -------
        pd.DataFrame
            The data with the columns renamed
        """
        data = data.rename(columns={
            "WindSpeed (knots)": "wspd",
            "WindDir (deg)": "wdir",
            "Int0 (knots)": "cspd",
            "Dir0 (deg)": "cdir",
            "SeaHm0 (m)": "swvht_sea",
            "SeaPeakPeriod (s)": "swvdir_sea",
            "SeaPeakDir (deg)": "tp_sea",
            "SwellHm0 (m)": "swvht_swell",
            "SwellPeakPeriod (s)": "tp_swell",
            "SwellPeakDir (deg)": "wvdir_swell",
            "SeaLevel (m)": "water_level",
        })
        current_date = datetime.now().date()
        data_time = data.index.values[0]
        hour, minute = map(int, data_time.split(":"))
        updated_datetime = datetime.combine(current_date,
                                            datetime.min.time()).replace(hour=hour,
                                                                         minute=minute)
        data.index = [updated_datetime]
        data.index.name = "date_time"
        data.reset_index(inplace=True)
        data["date_time"] = pd.to_datetime(data["date_time"])
        return data

    def _prepare_data(self, data):
        """ Prepare the data

        Parameters
        ----------
        data : pd.DataFrame
            The data to be prepared

        Returns
        -------
        pd.DataFrame
            The prepared data
        """
        data = data.replace(
            to_replace=["None", None, "NULL", "MM", ""], value=np.nan
        )

        columns = data.drop(columns="date_time").columns
        for column in columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

        data.loc[data.wspd.notnull(), "wspd"] = (
            data.wspd[data.wspd.notnull()] * 1.94384
        ).round(decimals=1)
        data.loc[data.cspd.notnull(), "cspd"] = (
            data.cspd[data.cspd.notnull()] * 1.94384
        ).round(decimals=1)
        data.reset_index(drop=True, inplace=True)
        return data


    def get_data_html(self, attrs: str, soup: BeautifulSoup) -> float:
        """Get data from the html

        Parameters
        ----------
        attrs : str
            The attributes
        soup : BeautifulSoup
            The soup

        Returns
        -------
        float
            The value
        """
        try:
            value = float(soup.find("div", {"id": attrs}).get_text(strip=True))
        except:
            value = np.nan
        return value

    def logging(self, driver: webdriver.Chrome) -> webdriver.Chrome:
        """Login in the website

        Parameters
        ----------
        driver : webdriver.Chrome
            The driver

        Returns
        -------
        webdriver.Chrome
            The driver
        """
        time.sleep(10)
        driver.find_element(By.CSS_SELECTOR, "#id_username").send_keys(
            os.getenv("SE_USER")
        )
        driver.find_element(By.CSS_SELECTOR, "#id_password").send_keys(
            os.getenv("SE_PWD")
        )
        driver.find_element(By.CSS_SELECTOR, "#wp-submit").click()
        time.sleep(10)
        return driver
