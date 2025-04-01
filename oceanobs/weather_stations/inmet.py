import warnings
import numpy as np
import pandas as pd
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from oceanobs.oceanobs import Oceanobs
from oceanobs.utils.utils import quit_driver

warnings.filterwarnings("ignore")


class Inmet(Oceanobs):
    def __init__(
        self,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(n_workers=n_workers)
        self.base_url = "https://tempo.inmet.gov.br/TabelaEstacoes"
        self.stations_url = "https://apimapas.inmet.gov.br"

    def get_stations(self, station_type: str = "automatic") -> pd.DataFrame:
        """Get stations from Aqualink buoy

        Returns
        -------
        pd.DataFrame
            The stations
        """
        url_address = self.stations_url + "/estacoes"
        response = requests.get(url_address)
        if response.status_code != 200:
            self.logger.error("Error getting stations from %s", url_address)
            return
        stations = response.json()
        if station_type == "automatic":
            stations = stations["estacoes"]["automaticas"]
        else:
            stations = stations["estacoes"]["convencionais"]
        station_list = []
        for key in stations:
            for station in stations[key]:
                station_list.append(station)

        stations_df = pd.DataFrame(station_list)
        stations_df = self._prepare_stations(stations_df)

        return stations_df

    def _prepare_stations(self, stations: pd.DataFrame) -> pd.DataFrame:
        """Prepare the stations metadata

        Parameters
        ----------
        stations : pd.DataFrame
            The stations metadata

        Returns
        -------
        pd.DataFrame
            The prepared stations metadata
        """
        df_stations = stations.copy()[["codigo", "nome", "latitude", "longitude"]]
        gdf_stations = self._convert_to_gdf(df_stations)
        gdf_stations.rename(columns={"codigo": "identifier", "nome": "name"}, inplace=True)
        return gdf_stations

    def get_data(self, station, add_columns: list = None) -> tuple:
        """Get data from a station

        Parameters
        ----------
        station : dict
            Station information
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        tuple
            The data and the error message
        """
        print(station["identifier"])
        driver = self.create_driver()
        url = self.base_url + "/" + station["identifier"]
        print(station["identifier"])
        try:
            driver.get(url)
        except Exception as e:
            quit_driver(driver)
            return None, str(e)

        # wait until table with class "ui blue celled striped unstackable table" is present
        wait = WebDriverWait(driver, 15)
        try:
            wait.until(ec.presence_of_element_located((By.CLASS_NAME, "ui.blue.celled.striped.unstackable.table")))
        except Exception as e:
            quit_driver(driver)
            return None, str(e)
        data = pd.read_html(driver.page_source, decimal=",", thousands=".")[0]
        data = self._rename_columns(data)
        data = self._prepare_data(data)
        data = self._add_columns(data, add_columns, station)
        quit_driver(driver)
        return data, None

    def _rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename columns

        Parameters
        ----------
        data : pd.DataFrame
            Data to rename columns

        Returns
        -------
        pd.DataFrame
            The data with renamed columns
        """
        data = data.iloc[:, [0, 1, 2, 11, 14, 15, 16]]
        columns = [
            "date",
            "hour",
            "atmp",
            "pres",
            "wspd",
            "wdir",
            "gust",
        ]
        data.columns = columns
        data["hour"] = (data["hour"] / 100).astype(int).astype("str").str.zfill(2)
        data["date_time"] = pd.to_datetime(data["date"] + data["hour"], format="%d/%m/%Y%H")
        data.drop(columns=["date", "hour"], inplace=True)
        return data

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare the data

        Parameters
        ----------
        data : pd.DataFrame
            The data to be prepared

        Returns
        -------
        pd.DataFrame
            The prepared data
        """
        data = data.replace(to_replace=["None", None, "NULL", " ", ""], value=np.nan)
        columns = [
            "atmp",
            "pres",
            "wspd",
            "wdir",
            "gust",
        ]
        data = data.dropna(subset=columns, how="all")
        return data
