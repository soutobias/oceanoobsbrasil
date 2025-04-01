"""WaveCheck data module"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from datetime import datetime
from itertools import chain

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from oceanobs.oceanobs import Oceanobs


class WaveCheck(Oceanobs):
    """Get data from Wave Check

    This class is used to get data from Wave Check.

    Parameters
    ----------
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """

    def __init__(
        self,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(n_workers=n_workers)
        self.base_url = "https://www.waves.com.br/"

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Wave Check

        Returns
        -------
        pd.DataFrame
            The stations
        """
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        menu = soup.find("ul", {"id": "menu-td-demo-header-menu-1"})
        menus = menu.find_all("a")
        hrefs = []
        for item in menus:
            href = item.attrs["href"]
            if "condicao" in href:
                hrefs.append({"name": item.text, "href": href})
        stations = []
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            futures = [executor.submit(partial(self.get_station, href=href)) for href in hrefs]
            for future in tqdm(as_completed(futures), desc="Get Stations", total=len(futures)):
                station = future.result()
                if len(station) > 0:
                    stations.append(station)
        stations = list(chain(*stations))
        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)
        return stations

    def get_station(self, href: dict) -> dict:
        """Get station from Wave Check

        Parameters
        ----------
        href : dict
            Dictionary with the href

        Returns
        -------
        dict
            The station
        """
        response = requests.get(href["href"])
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "table_ws"})
        tds = table.find_all("td")
        stations_local = []
        for td in tds:
            data_link = td.attrs.get("data-link")
            data_geo = td.attrs.get("data-geo")
            if data_link and data_geo:
                name = href["name"] + "_" + data_link.split("/")[-2]
                latitude, longitude = data_geo.split("_")
                data_link = data_link.replace(f"{self.base_url}surf/ondas/picos/", "")
                station = {
                    "identifier": data_link,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "name": name,
                }
                stations_local.append(station)
        return stations_local

    def get_data(self, station, add_columns: list = None) -> pd.DataFrame:
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
        url = f"{self.base_url}surf/ondas/picos/{station['identifier']}"
        try:
            response = requests.get(str(url))
        except Exception as e:
            error = f"Error getting data from {station['name']}: {str(e)}"
            return None, error
        soup = BeautifulSoup(response.text, "html.parser")
        has_data = soup.find("div", {"class": "pico_header_pico"})
        if has_data:
            swvht_part = soup.find("td", {"id": "forecast_wave_size"}).get_text(strip=True)

            try:
                [k1, _] = swvht_part.split("m")
                swvht = float(k1)
            except Exception:
                swvht = 0

            wvdir_part = soup.find("td", {"id": "forecast_wave_direction"}).get_text(strip=True)
            wvdir = str(wvdir_part).lower()
            wvdir = self._convert_wvdir(wvdir)
            date_time = datetime.now()
            date_time = date_time.replace(minute=0, second=0, microsecond=0)

            values = np.array([date_time, swvht, wvdir])
            columns = ["date_time", "swvht", "wvdir"]

            data = pd.DataFrame(values).T
            data.columns = columns
            if add_columns:
                if "id" in add_columns:
                    data["station_id"] = station["id"]
            return data, None
        else:
            error = f"No data for {station['name']}"
            return None, error

    def _convert_wvdir(self, wvdir: str) -> float:
        """Convert the wave direction to degrees

        Parameters
        ----------
        wvdir : str
            Wave direction

        Returns
        -------
        float
            The wave direction in degrees
        """
        direction_map = {
            "norte": 0,
            "norte-nordeste": 22,
            "norte nordeste": 22,
            "nordeste": 45,
            "nordeste-leste": 67,
            "nordeste leste": 67,
            "leste nordeste": 67,
            "leste-nordeste": 67,
            "leste": 90,
            "sudeste-leste": 112,
            "sudeste leste": 112,
            "leste sudeste": 112,
            "sudeste": 135,
            "sul-sudeste": 157,
            "sul sudeste": 157,
            "sudeste sul": 157,
            "sudeste-sul": 157,
            "sul": 180,
            "sul-sudoeste": 202,
            "sul sudoeste": 202,
            "sudoeste-sul": 202,
            "sudoeste sul": 202,
            "sudoeste": 225,
            "sudoeste-oeste": 247,
            "sudoeste oeste": 247,
            "oeste-sudoeste": 247,
            "oeste sudoeste": 247,
            "oeste": 270,
            "noroeste-oeste": 292,
            "noroeste oeste": 292,
            "oeste-noroeste": 292,
            "oeste noroeste": 292,
            "noroeste": 315,
            "noroeste-norte": 337,
            "noroeste norte": 337,
            "norte-noroeste": 337,
            "norte noroeste": 337,
            "não informado": np.nan,
        }

        return direction_map.get(wvdir, np.nan)
