import datetime
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from oceanobs.oceanobs import Oceanobs

class ShipObservations(Oceanobs):
    """ Ship Observations data collection class

    This class is used to collect data from the Ship Observations.

    Parameters
    ----------
    lat_lon_limits : dict, optional
        Latitude and longitude limits, by default None
    """
    def __init__(self,
                 lat_lon_limits: dict = None,
                 **kwargs):
        super().__init__(lat_lon_limits=lat_lon_limits)
        self.base_url = f"https://www.ndbc.noaa.gov/ship_obs.php?uom=M&time=12"

    def get(self,
            **kwargs) -> pd.DataFrame:
        """Get the data from the Ship Observations

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.logger.error(err)
            return
        soup = BeautifulSoup(response.text, "html.parser")

        lines = soup.find_all("pre")
        new_datas = []
        first_loop = True
        for line in lines:
            inner_lines = line.find_all("span")
            first_element = 1
            for inner_line in inner_lines:
                if first_element:
                    first_element = 0
                    new_header = inner_line.get_text(strip=True)
                    new_header = new_header.replace("B", " B")
                    new_header = re.sub(" +", ",", new_header).split(",")
                else:
                    new_data = inner_line.get_text(strip=True)
                    new_data = new_data.replace("B", " B")
                    new_data = re.sub(" +", ",", new_data).split(",")
                    new_datas.append(new_data)
            if first_loop:
                first_loop = False
                data = pd.DataFrame(new_datas)
            else:
                array = pd.DataFrame(new_datas)

                data = pd.concat([data, array])

        data.columns = new_header[: len(data.columns)]

        data.replace("-", np.nan, inplace=True)

        data["HOUR"] = (data["HOUR"].astype(int) / 100).astype(int)
        data["date_time"] = data["HOUR"].apply(lambda hour: self.calculate_date(hour))

        data = self._rename_columns(data)
        data = self._prepare_data(data)
        data = self._convert_to_gdf(data)
        data = data[
            (data.latitude > self.lat_lon_limits["min_lat"])
            & (data.latitude < self.lat_lon_limits["max_lat"])
            & (data.longitude < self.lat_lon_limits["max_lon"])
            & (data.longitude > self.lat_lon_limits["min_lon"])
        ]
        data.rename(columns={"data_type": "station_type"}, inplace=True)
        data["station_type"] = "ship"

        return data

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
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
        data = self.convert_to_numeric(data)
        data.wspd[data.wspd.notnull()] = (
            data.wspd[data.wspd.notnull()] * 1.94384
        ).round(decimals=1)
        data.fillna(np.nan, inplace=True)
        data = data.replace(
            to_replace=["None", None, "NULL", " ", ""], value=np.nan
        )

        return data


    def _rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename the columns of the DataFrame

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with the data

        Returns
        -------
        pd.DataFrame
            DataFrame with the renamed columns
        """
        data = data[
            [
                "SHIP",
                "date_time",
                "LAT",
                "LON",
                "WDIR",
                "WSPD",
                "WVHT",
                "DPD",
                "PRES",
                "ATMP",
                "WTMP",
                "DEWP",
                "S1HT",
                "S1DIR",
            ]
        ].copy()
        data.columns = [
            "data_type",
            "date_time",
            "latitude",
            "longitude",
            "wdir",
            "wspd",
            "swvht",
            "tp",
            "pres",
            "atmp",
            "sst",
            "dewpt",
            "swvht_swell",
            "wvdir_swell",
        ]
        return data

    def calculate_date(self, hour: int) -> datetime:
        """Calculate the date

        Parameters
        ----------
        hour : int
            The hour to calculate the date

        Returns
        -------
        datetime
            The calculated date
        """
        start_date = datetime.now(timezone.utc) - timedelta(hours=12)
        end_date = datetime.now(timezone.utc)
        if hour >= end_date.hour + 2:
            value = start_date
            value = value.replace(hour=hour)
        else:
            value = end_date
            value = value.replace(hour=hour)

        value = value.replace(minute=0)
        value = value.replace(second=0)
        value = value.replace(microsecond=0)
        return value
