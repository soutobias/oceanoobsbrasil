"""This module contains the class Pirata that is used to download data from the PIRATA buoys."""

import json
import os
import urllib.request

import numpy as np
import pandas as pd

from oceanobs.oceanobs import (
    Oceanobs,
)


class Pirata(Oceanobs):
    """Get data from PIRATA buoys

    This class is used to get data from PIRATA buoys.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    base_url : str, optional
        Base URL for the data, by default None
    """

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        n_workers: int = 1,
        base_url: str = None,
        **kwargs,
    ):
        super().__init__(start_date=start_date, end_date=end_date, n_workers=n_workers)
        self.base_url = "https://www.ndbc.noaa.gov/data/realtime2/" if not base_url else base_url

    def get_stations(self) -> pd.DataFrame:
        """Get stations from PIRATA buoys

        The stations are read from a json file.

        Returns
        -------
        pd.DataFrame
            The stations
        """

        file_path = os.path.join(os.path.dirname(__file__), "../data/buoy_pirata.json")

        with open(file_path, "r") as file:
            stations = json.load(file)

        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)

        return stations

    def get_data(self, station, start_date=None, end_date=None, add_columns: list = None) -> pd.DataFrame:
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
        url_address = f"{self.base_url}{station['identifier']}.txt"
        try:
            with urllib.request.urlopen(url_address) as url:
                data = pd.read_csv(url, sep="\s+")
                data = data.iloc[1:]
        except Exception as e:
            error = f"Error getting data from {station['name']}: {str(e)}"
            return None, error

        data = self._rename_columns(data)
        # filter data by start and end date
        data = data[(data.date_time >= self.start_date) & (data.date_time <= self.end_date)]
        if data.empty:
            error = f"No data available for {station['name']} between {self.start_date} and {self.end_date}"
            return data, error
        data = self._prepare_data(data)

        if add_columns:
            if "id" in add_columns:
                data["station_id"] = station["id"]

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
        data = data.replace(to_replace=["None", None, "NULL", "MM", ""], value=np.nan)
        columns = data.drop(columns="date_time").columns
        for column in columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

        data.loc[data.wspd.notnull(), "wspd"] = (data.wspd[data.wspd.notnull()] * 1.94384).round(decimals=1)
        data.loc[data.gust.notnull(), "gust"] = (data.gust[data.gust.notnull()] * 1.94384).round(decimals=1)
        return data

    def _rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename the columns

        Parameters
        ----------
        data : pd.DataFrame
            The data

        Returns
        -------
        pd.DataFrame
            The data with the renamed columns
        """

        rename_columns = {
            "#YY": "year",
            "MM": "month",
            "DD": "day",
            "hh": "hour",
            "mm": "minute",
        }
        data.rename(columns=rename_columns, inplace=True)
        data["date_time"] = pd.to_datetime(data.iloc[:, 0:4])

        data = data[
            [
                "date_time",
                "WDIR",
                "WSPD",
                "GST",
                "WVHT",
                "DPD",
                "MWD",
                "PRES",
                "ATMP",
                "WTMP",
                "DEWP",
                "VIS",
            ]
        ]

        data.columns = [
            "date_time",
            "wdir",
            "wspd",
            "gust",
            "swvht",
            "tp",
            "wvdir",
            "pres",
            "atmp",
            "sst",
            "dewpt",
            "visibility",
        ]

        return data
