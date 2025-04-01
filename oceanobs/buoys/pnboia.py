"""PNBOIA class module"""

import os

import numpy as np
import pandas as pd
import requests
from dotenv import (
    load_dotenv,
)

from oceanobs.oceanobs import (
    Oceanobs,
)

load_dotenv()


class Pnboia(Oceanobs):
    """PNBOIA class

    This class is used to download data from PNBOIA buoys.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(start_date=start_date, end_date=end_date, n_workers=n_workers)
        self.base_url = "http://52.67.222.63/v1/"
        self._token = os.getenv("REMOBS_TOKEN")

    def get_stations(self) -> pd.DataFrame:
        """Get the stations metadata

        Returns
        -------
        pd.DataFrame
            The stations metadata
        """
        url_address = f"{self.base_url}moored/buoys?token={self._token}&response_type=json"
        response = requests.get(url_address)
        if response.status_code != 200:
            self.logger.error("Error getting stations from %s", url_address)
            return
        stations = response.json()
        stations = pd.DataFrame(stations)
        stations = self._prepare_stations(stations)

        return stations

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
        stations["status"] = stations["mode"].apply(lambda x: "Active" if x == "FUNDEADA" else "Inactive")
        stations["identifier"] = stations["api_endpoint"] + "?buoy_id=" + stations["buoy_id"].astype(str)
        stations = stations.dropna(subset=["identifier", "latitude", "longitude"])
        df_stations = stations.copy()[["name", "identifier", "latitude", "longitude"]]
        gdf_stations = self._convert_to_gdf(df_stations)
        return gdf_stations

    def get_data(self, station, start_date=None, end_date=None, add_columns: list = None) -> tuple:
        """Get data from a station

        Parameters
        ----------
        station : dict
            Station information
        start_date : str
            Start date in the format "%Y-%m-%dT%H:%M:%S"
        end_date : str
            End date in the format "%Y-%m-%dT%H:%M:%S"
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        tuple
            The data and the error message
        """
        if start_date:
            self.start_date = self._validate_date(start_date)
        if end_date:
            self.end_date = self._validate_date(end_date)
        if self.start_date >= self.end_date:
            return None, "Start date must be before end date"
        if not add_columns:
            add_columns = ["name"]
        url = f"{self.base_url}{station['identifier']}&start_date={self.start_date}&end_date={self.end_date}&token={self._token}"
        response = requests.get(url)
        if response.status_code != 200:
            error = f"Error getting data from {station['name']}"
            return None, error
        try:
            data = response.json()
            data = pd.DataFrame(data)
            for column in data.columns:
                try:
                    data[column] = pd.to_numeric(data[column])
                except Exception:
                    pass
            data["date_time"] = pd.to_datetime(data["date_time"], format="%Y-%m-%dT%H:%M:%S")
            data.sort_values("date_time", inplace=True)
            data = self._rename_columns(data)
            data = data.copy()

            if data.empty:
                error = f"Error getting data from {station['name']}"
                return None, error
            else:
                data = self._prepare_data(data)
                data = self.remove_dup_columns(data)

                if add_columns:
                    if "id" in add_columns:
                        data["station_id"] = station["id"]
                    if "name" in add_columns:
                        data["name"] = station["name"]
        except Exception as e:
            error = str(e) + f" - {station['name']}"
            return None, error

        return data, None

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare the data

        Parameters
        ----------
        data : pd.DataFrame
            The data

        Returns
        -------
        pd.DataFrame
            The prepared data
        """
        if "wspd" in data.columns:
            data.wspd = data.wspd * 1.94384
        if "gust" in data.columns:
            data.gust = data.gust * 1.94384

        data = data.replace(to_replace=["None", None, "NULL", " ", ""], value=np.nan)
        data = data.dropna(subset=["date_time"])
        return data

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
        columns = data.columns
        selected_columns = [
            "date_time",
            "rh",
            "pres",
            "atmp",
            "dewpt",
            "wspd1",
            "wdir1",
            "gust1",
            "sst",
            "swvht1",
            "mxwvht1",
            "tp1",
            "wvdir1",
        ]
        columns = [col for col in columns if col in selected_columns]
        data = data.copy()[columns]
        if "wspd1" in data.columns:
            data.rename(columns={"wspd1": "wspd"}, inplace=True)
        if "wdir1" in data.columns:
            data.rename(columns={"wdir1": "wdir"}, inplace=True)
        if "gust1" in data.columns:
            data.rename(columns={"gust1": "gust"}, inplace=True)
        if "swvht1" in data.columns:
            data.rename(columns={"swvht1": "swvht"}, inplace=True)
        if "mxwvht1" in data.columns:
            data.rename(columns={"mxwvht1": "mxwvht"}, inplace=True)
        if "tp1" in data.columns:
            data.rename(columns={"tp1": "tp"}, inplace=True)
        if "wvdir1" in data.columns:
            data.rename(columns={"wvdir1": "wvdir"}, inplace=True)
        return data
