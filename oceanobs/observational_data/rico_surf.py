"""Rico Surf data handler."""

import re
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from datetime import (
    datetime,
)
from functools import (
    partial,
)

import numpy as np
import pandas as pd
import requests
from bs4 import (
    BeautifulSoup,
)
from tqdm import (
    tqdm,
)

from oceanobs.oceanobs import (
    Oceanobs,
)


class RicoSurf(Oceanobs):
    """Get data from Rico Surf

    This class is used to get data from Rico Surf.

    Parameters
    ----------
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    base_url : str, optional
        Base URL for the data, by default None
    urls : list, optional
        URLs for the data, by default
    """

    def __init__(
        self,
        n_workers: int = 1,
        base_url: str = None,
        urls: list = None,
        **kwargs,
    ):
        super().__init__(n_workers=n_workers)
        self.base_url = "https://ricosurf.com.br/" if not base_url else base_url
        self.urls = ["condicoes-do-mar-rio-de-janeiro", "condicoes-do-mar-sao-paulo"] if not urls else urls
        self.beaches = self.beaches_with_data()

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Rico Surf

        Returns
        -------
        pd.DataFrame
            The stations
        """
        names, hrefs = [], []
        stations = []
        errors = []
        for url in self.urls:
            url = self.base_url + url
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            for zona_pico in soup.find_all("div", attrs={"class": "zonas_picos"}):
                lis = zona_pico.find_all("li")
                for li in lis:
                    a_tag = li.find("a")
                    names.append(a_tag.text.strip())
                    hrefs.append(a_tag.attrs["href"])
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            futures = [executor.submit(partial(self.get_station, href=href, name=name)) for name, href in zip(names, hrefs)]
            for future in tqdm(as_completed(futures), desc="Get Stations", total=len(futures)):
                station, error = future.result()
                if station is not None:
                    stations.append(station)
                else:
                    errors.append(error)
        if len(errors) > 0:
            self.logger.error("Errors: %s", errors)
        stations = pd.DataFrame(stations)
        stations = self._convert_to_gdf(stations)
        return stations

    def get_station(self, href: str, name: str) -> tuple:
        """Get station from Rico Surf

        Parameters
        ----------
        href : str
            The station href
        name : str
            The station name

        Returns
        -------
        tuple
            The station and the error
        """

        url = f"{self.base_url}{href}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        link_with_position = self._extract_google_maps_link(soup)
        if link_with_position:
            lat_lon = self._extract_lat_lon(link_with_position)
            if lat_lon:
                lat, lon = lat_lon
                station = {
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "identifier": href,
                }
                return station, None
        error = f"Error getting station {name}"
        return None, error

    def get_data(self, station: dict, add_columns: list = None) -> tuple:
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

        if self.beach_has_data(station):
            url = f"{self.base_url}{station['identifier']}"
            response = requests.get(str(url))
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                swvht_soup = soup.find("div", {"class": "h5 text-primary margin-xxs-bottom"}).get_text(strip=True).replace(",", ".")
                swvht = float(swvht_soup[0:-1])

                tp_sst_soup = soup.find_all("div", attrs={"class": "h5 no-margin text-primary"})
                tp = tp_sst_soup[0].get_text(strip=True).replace(",", ".")
                tp = float(tp[0:-1])
                sst = tp_sst_soup[1].get_text(strip=True)
                sst = float(sst[0:-2])
                wvdir = soup.find("div", {"class": "small line-height-xs"}).get_text(strip=True).lower()
                wvdir = self._convert_wvdir(wvdir)

                date_time = datetime.now()
                date_time = date_time.replace(minute=0, second=0, microsecond=0)

                values = np.array([date_time, swvht, tp, sst, wvdir])
                columns = ["date_time", "swvht", "tp", "sst", "wvdir"]

                data = pd.DataFrame(values).T
                data.columns = columns
                data = self._prepare_data(data)
                if add_columns:
                    if "id" in add_columns:
                        data["station_id"] = station["id"]
            except Exception:
                error = f"Error getting data from {station['name']}"
                return None, error
        else:
            error = f"Error getting data from {station['name']}"
            return None, error
        return data, None

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
        data = data.replace(to_replace=["None", None, "NULL", "MM", ""], value=np.nan)
        return data

    def _extract_google_maps_link(self, soup: BeautifulSoup) -> str:
        """Extract the Google Maps link from the soup

        Parameters
        ----------
        soup : BeautifulSoup
            The soup

        Returns
        -------
        str
            The Google Maps link
        """
        iframe = soup.find("iframe", src=re.compile(r"https://www\.google\.com/maps/embed\?pb="))
        if iframe:
            return iframe["src"]
        return None

    def _extract_lat_lon(self, embed_url: str) -> tuple:
        """Extract the latitude and longitude from the embed URL

        Parameters
        ----------
        embed_url : str
            The embed URL

        Returns
        -------
        tuple
            The latitude and longitude
        """
        match = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", embed_url)
        if match:
            lon, lat = match.groups()
            return float(lat), float(lon)
        return None

    def _convert_wvdir(self, wvdir: str) -> float:
        """Convert the wave direction to degrees

        Parameters
        ----------
        wvdir : str
            The wave direction

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

        return direction_map.get(wvdir, wvdir)

    def beach_has_data(self, station: dict) -> bool:
        """Check if the beach has data

        Parameters
        ----------
        station : dict
            The station

        Returns
        -------
        bool
            True if the beach has data, False otherwise
        """
        if station["name"] in self.beaches:
            return True
        return False

    def beaches_with_data(self) -> list:
        """Get the beaches with data

        Returns
        -------
        list
            The beaches with data
        """
        beaches_with_data = []
        for url in self.urls:
            url = f"{self.base_url}{url}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            beaches = soup.find_all("li", attrs={"data-toggle": "popover"})
            for beach in beaches:
                if beach["data-content"][-10:-6] != "zado":
                    beaches_with_data.append(beach.text.strip()[1:])
        return beaches_with_data
