"""Class to get data from the Espirito Santo buoys"""

import json
import os
from datetime import (
    datetime,
    timedelta,
)

import numpy as np
import pandas as pd
import requests
from bs4 import (
    BeautifulSoup,
)
from dotenv import (
    load_dotenv,
)

from oceanobs.oceanobs import (
    Oceanobs,
)

load_dotenv()


class ESBuoy(Oceanobs):
    """Get data from Espirito Santo buoys

    This class is used to get data from Espirito Santo buoys.

    Parameters
    ----------
    base_url : str, optional
        Base URL for the data, by default None
    """

    def __init__(
        self,
        base_url: str = None,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://service.vports.com.br/online/sgp/RetornaDadosBoiaAtoN/" if not base_url else base_url

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Espirito Santo buoys

        The stations are read from a json file.

        Returns
        -------
        pd.DataFrame
            The stations
        """
        file_path = os.path.join(os.path.dirname(__file__), "../data/buoy_es.json")

        with open(file_path, "r") as file:
            stations = json.load(file)

        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)
        return stations

    def get_data(self, station, add_columns: list = None) -> tuple:
        """Get data from a station

        Parameters
        ----------
        station : dict
            The station information
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        tuple
            The data and the error message
        """
        if not add_columns:
            add_columns = ["name"]
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")

        try:
            date_time = soup.find("h4", {"class": "titulo"}).text
            date_time = datetime.strptime(date_time, "%d/%m/%Y %H:%M:%S")
        except Exception as e:
            error = "Error getting data from Espirito Santo:" + str(e)
            return None, error

        wdir = self.get_data_html(soup, "data-wind-direction-deg")
        wspd = self.get_data_html(soup, "data-wind-speed-knot")
        atmp = self.get_data_html(soup, "data-air-temperature")
        swvht = self.get_data_html(soup, "data-height-wave")
        wvdir = self.get_data_html(soup, "data-wave-direction")
        tp = self.get_data_html(soup, "data-peak-wave-period")
        pres = self.get_data_html(soup, "data-atmosferic-pressure")
        rh = self.get_data_html(soup, "data-relative-humidity")

        if (
            np.isnan(wdir)
            and np.isnan(wspd)
            and np.isnan(atmp)
            and np.isnan(swvht)
            and np.isnan(wvdir)
            and np.isnan(tp)
            and np.isnan(pres)
            and np.isnan(rh)
        ):
            error = "Error getting data from Espirito Santo"
            return None, error

        values = np.array([date_time, wdir, wspd, atmp, swvht, wvdir, tp, pres, rh])
        columns = [
            "date_time",
            "wdir",
            "wspd",
            "atmp",
            "swvht",
            "wvdir",
            "tp",
            "pres",
            "rh",
        ]
        data = pd.DataFrame(values).T
        data.columns = columns

        data.date_time = data.date_time + timedelta(hours=3)

        if add_columns:
            if "id" in add_columns:
                data["station_id"] = station["id"]

        return data, None

    def get_data_html(self, soup, attrs):
        try:
            value = float(soup.find("h3", {attrs: True})[attrs])
        except Exception:
            value = np.nan
        return value
