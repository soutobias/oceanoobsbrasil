from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import io
import re

import numpy as np
import pandas as pd
import requests
from metar import Metar
from tqdm import tqdm
from oceanobs.oceanobs import Oceanobs
from oceanobs.oceanobs_handler.db_handler import DbHandler

class MetarStations(Oceanobs):
    """ Simcosta class

    This class is used to download data from SIMCOSTA buoys.

    Parameters
    ----------
    hours : list, optional
        The hours to get the data, by default None, which means all hours
    lat_lon_limit : dict, optional
        Latitude and longitude limits, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """
    def __init__(
        self,
        hours: list = None,
        lat_lon_limits: dict = None,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(
                        lat_lon_limits=lat_lon_limits,
                         n_workers=n_workers)
        self.base_url = "https://tgftp.nws.noaa.gov/data/observations/metar"
        self.stations_url = "https://weather.ral.ucar.edu/surface/stations.txt"
        if isinstance(hours, int):
            hours = [hours]
        self.hours = hours if hours else list(range(24))
        # self.base_url = f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?{stations_brazil}&{stations_argentina}&{stations_chile}&{stations_uruguai}&{stations_antartica}&{stations_malvinas}&{datas}&year1={self.start_date.year}&month1={self.start_date.month}&day1={self.start_date.day}&year2={self.end_date.year}&month2={self.end_date.month}&day2={self.end_date.day}&tz=Etc%2FUTC&format=onlycomma&latlon=no&elev=no&missing=empty&trace=empty&direct=no&report_type=1&report_type=2"

    def get_stations(self) -> pd.DataFrame:
        """ Get the stations metadata

        Returns
        -------
        pd.DataFrame
            The stations metadata
        """
        response = requests.get(self.stations_url)
        if response.status_code != 200:
            self.logger.error("Error getting stations from %s", self.stations_url)
            return
        pattern = re.compile(
            r"(?P<station>.*?)\s+(?P<icao>\b[A-Z]{4}\b)\s+.*?(?P<lat>\d{2} \d{2}[NS])\s+(?P<lon>\d{3} \d{2}[EW])"
        )
        pattern = re.compile(
            r"(?P<station>.{19})\s+(?P<icao>\b[A-Z]{4}\b)\s+.*?(?P<lat>\d{2} \d{2}[NS])\s+(?P<lon>\d{3} \d{2}[EW])"
        )
        matches = pattern.findall(response.text)
        stations = pd.DataFrame(
            {
                "name": [match[0].strip() for match in matches],
                "identifier": [match[1] for match in matches],
                "latitude": [self._parse_coordinate(match[2]) for match in matches],
                "longitude": [self._parse_coordinate(match[3]) for match in matches],
            }
        )
        if self.lat_lon_limit:
            stations = self._filter_stations(stations)

        return self._convert_to_gdf(stations)

    def _filter_stations(self, stations: pd.DataFrame) -> pd.DataFrame:
        """ Filter the stations

        Parameters
        ----------
        stations : pd.DataFrame
            The stations to be filtered

        Returns
        -------
        pd.DataFrame
            The filtered stations
        """
        stations = stations[
            (stations["latitude"] >= self.lat_lon_limit["min_lat"])
            & (stations["latitude"] <= self.lat_lon_limit["max_lat"])
            & (stations["longitude"] >= self.lat_lon_limit["min_lon"])
            & (stations["longitude"] <= self.lat_lon_limit["max_lon"])
        ]
        return stations

    def get_data(self,
                 station,
                 add_columns: list = None) -> tuple:

        """ Get the last available data from a station

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

        url = f"{self.base_url}/stations/{station['identifier']}.TXT"
        response = requests.get(url)
        if response.status_code != 200:
            error = f"Error getting data from {station['name']}"
            return None, error

        try:
            data = self._parse_metar(response.text.split("\n")[1])
        except Exception as e:
            error = f"Error parsing METAR data for {station['name']}: {str(e)}"
            return None, error

        data = pd.DataFrame([data])
        data.drop(columns=["station"], inplace=True)
        data = self._prepare_data(data)
        data = self._add_columns(data, add_columns, station)

        return data, None


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
        data = data.copy().replace(
            to_replace=["None", None, "NULL", " ", ""], value=np.nan
        )
        return data

    def _parse_metar(self, response_text: str) -> dict:
        """ Parse the METAR data

        Parameters
        ----------
        response_text : str
            The METAR data to be parsed

        Returns
        -------
        dict
            The parsed data
        """
        try:
            obs = Metar.Metar(response_text)
        except Exception as e:
            error = f"{str(e)}"
            raise Exception(error)
        data = {
            "station": obs.station_id,
            "date_time": obs.time.strftime("%Y-%m-%dT%H:%M:%S") if obs.time else None,
            "atmp": obs.temp.value() if obs.temp else None,
            "visibility": obs.vis.value() if obs.vis else None,
            "dewpt": obs.dewpt.value() if obs.dewpt else None,
            "wdir": obs.wind_dir.value() if obs.wind_dir else None,
            "wspd": obs.wind_speed.value() if obs.wind_speed else None,
            "gust": obs.wind_speed_peak.value() if obs.wind_speed_peak else None,
        }

        if not data["date_time"]:
            error = f"Missing essential data"
            raise Exception(error)

        return data

    def get(self,
            stations: pd.DataFrame = None,
            add_columns: list = None) -> pd.DataFrame:
        """Get data from the stations

        Parameters
        ----------
        stations : pd.DataFrame, optional
            DataFrame with the stations, by default None
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """

        if stations is None:
            self.stations = self.get_stations()
        else:
            self.stations = stations

        errors = []
        results = []
        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
                futures = [
                    executor.submit(self.get_single_hour, hour, session)
                    for hour in self.hours
                ]
                for future in tqdm(as_completed(futures), desc="Downloading data", total=len(futures)):
                    result, error = future.result()
                    if result is not None and not result.empty:
                        results.append(result)
                    if error:
                        errors.append(error)
        if len(self.errors) > 0:
            self.logger.error("Errors collecting data: %s", self.errors)

        if not results:
            return pd.DataFrame()
        results = pd.concat(results, ignore_index=True).drop_duplicates()
        results.rename(columns={"station": "identifier"}, inplace=True)
        stations_columns = ["id", "name", "identifier"] if "id" in self.stations.columns else ["name", "identifier"]
        stations = self.stations[stations_columns]
        results = results.merge(stations, how="left", left_on="identifier", right_on="identifier")
        results.drop(columns=["identifier"], inplace=True)
        results = results[results["name"].notnull()]
        results = self._prepare_data(results)
        if "id" in results.columns:
            results.rename(columns={"id": "station_id"}, inplace=True)
            results["station_id"] = results["station_id"].astype(int)
        results = self._add_columns(results, add_columns)

        return results

    def get_single_hour(self, hour: int, session: requests.Session) -> pd.DataFrame:
        """ Get the data for a single hour

        Parameters
        ----------
        hour : int
            The hour to get the data
        session : requests.Session
            The session to be used for the requests

        Returns
        -------
        pd.DataFrame
            The data
        """
        data_url = f"{self.base_url}/cycles/{hour:02}Z.TXT"
        try:
            response = session.get(data_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            return None, f"Error getting data from {hour}: {e}"
        all_data = []
        lines = response.text.split("\n")
        for line in lines:
            # check if line starts with number
            if not line:
                continue
            if not line[0].isdigit():
                try:
                    data = self._parse_metar(line)
                except Exception as e:
                    continue
                if data is not None:
                    all_data.append(data)
        data = pd.DataFrame(all_data)
        return data, None

    def _parse_coordinate(self, value: str) -> float:
        """Convert coordinate from DMS (degrees and minutes) format to decimal degrees.

        Parameters
        ----------
        value : str
            The coordinate in DMS format

        Returns
        -------
        float
            The coordinate in decimal degrees
        """
        degrees, minutes = map(str.strip, value[:-1].split(" "))
        decimal = int(degrees) + int(minutes) / 60
        return -decimal if value[-1] in {"S", "W"} else decimal



if __name__ == "__main__":
    Metar().get(save_bd=True)
