""" Class to get data from Pernambuco buoys """
import json
import os
import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from oceanobs.oceanobs import Oceanobs
from oceanobs.utils import quit_driver, uv2intdir
load_dotenv()

class PEBuoy(Oceanobs):
    """Get data from Pernambuco buoys"""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = os.getenv("PE_URL")

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Pernambuco buoys

        The stations are read from a json file.

        Returns
        -------
        pd.DataFrame
            The stations
        """

        file_path = os.path.join(os.path.dirname(__file__), "../data/buoy_pe.json")

        with open(file_path, "r") as file:
            stations = json.load(file)

        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)
        return stations

    def get_data(self,
                 station,
                 add_columns: list = None) -> tuple:
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
        except Exception as e:
            quit_driver(driver)
            return None, str(e)

        wait = WebDriverWait(driver, 15)
        wait.until(ec.visibility_of_element_located((By.XPATH, "//div[@id='Box01_1631']")))

        def get_element_text(element_id: str, data_type=float):
            """ Helper function to extract text from an element and convert it to the specified data type. """
            try:
                element_text = driver.find_element("id", element_id).text
                return data_type(element_text)
            except Exception:
                return None

        mwd = get_element_text("Box01_1631", int)
        hm0 = get_element_text("Box01_718")
        seapeakdir = get_element_text("Box04_1633", int)
        seahm0 = get_element_text("Box04_1627")
        swellpeakdir = get_element_text("Box07_1634", int)
        swellhm0 = get_element_text("Box07_1624")

        try:
            date_time = driver.find_element(By.XPATH,
                                             "//*[contains(text(), 'Latest data')]")
            date_time = date_time.text
            date_time = datetime.strptime(date_time[13:], "%Y-%m-%d %H:%M")
        except Exception as e:
            quit_driver(driver)
            return None, str(e)

        try:
            driver.find_element("xpath", "//a[contains(text(),'PÍER')]").click()
            time.sleep(10)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            wdir_part = soup.find(attrs={"id": "Box01_arrow"})
            uv_wind_velocity = re.findall(r"[+-]?\d+\.\d+", wdir_part.path.attrs["transform"])
            _, direc = uv2intdir(float(uv_wind_velocity[0]), float(uv_wind_velocity[1]))
            wdir = round(direc)

            wspd = round(float(soup.find(attrs={"id": "Box01_689"}).text), 2)
            gust = round(float(soup.find(attrs={"id": "Box01_690"}).text), 2)
        except Exception as e:
            wdir, wspd, gust = None, None, None

        values = np.array([
            date_time, mwd, hm0, seapeakdir, seahm0,
            swellpeakdir, swellhm0, wspd, gust, wdir
        ])
        columns = [
            "date_time", "wvdir", "swvht", "wvdir_sea", "swvht_sea",
            "wvdir_swell", "swvht_swell", "wspd", "gust", "wdir"
        ]
        data = pd.DataFrame(values).T
        data.columns = columns
        data = self._prepare_data(data, columns)

        if add_columns:
            if "id" in add_columns:
                data["station_id"] = station["id"]

        quit_driver(driver)

        return data, None

    def _prepare_data(self, data: pd.DataFrame, columns: list) -> pd.DataFrame:
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
        data = data.infer_objects(copy=False)
        data = data.replace(
            to_replace=["None", None, "NULL", " ", ""], value=np.nan
        )
        for column in columns:
            if column != "date_time":
                if isinstance(data[column], (pd.Series, list, tuple, np.ndarray)):
                    data[column] = pd.to_numeric(data[column], errors="coerce")
                else:
                    self.logger.warning(f"Column {column} is not a Series")
        return data
