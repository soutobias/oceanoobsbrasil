"""EpagriTide class"""

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import requests
from oceanobs.oceanobs import Oceanobs
from oceanobs.utils.utils import quit_driver


class EpagriTide(Oceanobs):
    """EpagriTide class

    This class is used to download data from Epagri tide stations.

    Parameters
    ----------
    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://ciram.epagri.sc.gov.br/index.php/maregrafos/"
        self.stations_url = "https://ciram.epagri.sc.gov.br/api/litoral-online-server/webresources/monitoramentolitoral/estacoesMapa"
        self.soup = None

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Pernambuco buoys

        The stations are read from a json file.

        Returns
        -------
        pd.DataFrame
            The stations
        """
        try:
            response = requests.post(self.stations_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.logger.error(err)
            return
        stations = response.json()
        stations = pd.DataFrame(stations["estacoes"])
        stations = stations[["estacao", "nome", "lat", "lon"]]
        stations.columns = ["identifier", "name", "latitude", "longitude"]
        stations = self._convert_to_gdf(stations)
        stations = stations.loc[stations.identifier > 2000]
        return stations

    def get_data(self, station, add_columns: list = None) -> tuple:
        """Get the last available data from a station

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
        self.scrape_page()
        page_stations = self._get_page_stations()
        page_tables = pd.read_html(str(self.soup))
        data = None
        for idx, page_station in enumerate(page_stations):
            if page_station in station["name"]:
                data = page_tables[idx]
                break
        if data is None:
            error = f"Error getting data from {station['name']}"
            return None, error

        data["date_time"] = pd.to_datetime(data.Topping, format="%d/%m %H:%M") + pd.offsets.DateOffset(years=datetime.now(timezone.utc).year - 1900)
        data = self._rename_columns(data)
        data = self._prepare_data(data)
        data = self._add_columns(data, add_columns, station)

        return data, None

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
        data = data[["Mare Obser.", "Residual", "Mare Astron", "date_time"]]
        data.columns = [
            "water_level",
            "meteorological_tide",
            "pred_water_level",
            "date_time",
        ]
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
        data = data.copy().replace(to_replace=["None", None, "NULL", " ", ""], value=np.nan)
        data = data.loc[np.isnan(data.water_level) is False]
        data.water_level = data.water_level / 100
        data.meteorological_tide = data.meteorological_tide / 100
        data.pred_water_level = data.pred_water_level / 100

        data.date_time = data.date_time + timedelta(hours=3)
        return data

    def _get_page_stations(self) -> pd.DataFrame:
        """Get the stations from the page

        Returns
        -------
        pd.DataFrame
            The stations
        """
        values = self.soup.find(attrs={"class": "row"}).find_all(attrs={"style": "font-size: 11pt;"})
        return [value.text for value in values]

    def scrape_page(self):
        if not self.soup:
            driver = self.create_driver()
            driver.get(self.base_url)
            time.sleep(30)
            self.soup = BeautifulSoup(driver.page_source, "html.parser")
            quit_driver(driver)


if __name__ == "__main__":
    EpagriTide().get()
