"""OceanObs class"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from functools import partial
from typing import Union

from geopandas import gpd
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from oceanobs.utils import END_DATE, LAT_LON_LIMITS, START_DATE, def_args_prefs

load_dotenv()

class Oceanobs:
    """OceanObs class

    This class is the base class for all the data collection classes.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """

    def __init__(self,
                 start_date: str = None,
                 end_date: str = None,
                 lat_lon_limits: list = None,
                 n_workers: int = 1,
                 ):
        self.logger = logging.getLogger(__name__)
        self.start_date = self._validate_date(start_date, is_start_date=True)
        self.end_date = self._validate_date(end_date, is_start_date=False)
        self.lat_lon_limits = self._validate_lat_lon_limits(lat_lon_limits)
        if self.start_date >= self.end_date:
            self.logger.error("Start date must be before end date")
            raise ValueError("Start date must be before end date")

        self.errors = []
        self.n_workers = n_workers

    def _validate_lat_lon_limits(self, lat_lon_limits: list = None) -> dict:
        """Validate the latitude and longitude limits

        Parameters
        ----------
        lat_lon_limits : list, optional
            List with the latitude and longitude limits, by default None

        Returns
        -------
        dict
            Dictionary with the latitude and longitude limits
        """
        if lat_lon_limits is None:
            lat_lon_limits = LAT_LON_LIMITS
        if not isinstance(lat_lon_limits, dict):
            self.logger.error("Invalid lat_lon_limits. Expected dict")
            raise ValueError("Invalid lat_lon_limits. Expected dict")

        if not all(key in lat_lon_limits for key in LAT_LON_LIMITS.keys()):
            self.logger.error(f"Invalid lat_lon_limits. Expected keys: {LAT_LON_LIMITS.keys()}")
            raise ValueError(f"Invalid lat_lon_limits. Expected keys: {LAT_LON_LIMITS.keys()}")

        return lat_lon_limits

    def _validate_date(self, date_str: str = None, is_start_date: bool = True) -> str:
        """Validates the date format and returns a datetime object.

        Parameters
        ----------
        date_str : str, optional
            Date string to validate, by default None
        is_start_date : bool, optional
            If the date is the start date, by default True
        """

        date_format = "%Y-%m-%dT%H:%M:%S"
        default_date = START_DATE if is_start_date else END_DATE
        if date_str is None:
            date_str = default_date
        try:
            datetime.strptime(date_str, date_format)
        except ValueError:
            self.logger.error(f"Invalid date format: {date_str}. Expected format: {date_format}")
            raise ValueError(f"Invalid date format: {date_str}. Expected format: {date_format}")
        return date_str

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
            self.stations = self.get_stations().iloc[:100]
        else:
            self.stations = stations

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            futures = [
                executor.submit(partial(self.get_data, station=station[1], add_columns=add_columns))
                for station in self.stations.iterrows()
            ]

            results = []
            for future in tqdm(as_completed(futures), desc="Downloading data", total=len(futures)):
                result, error = future.result()
                if result is not None and not result.empty:
                    results.append(result)
                if error:
                    self.errors.append(error)

        if len(self.errors) > 0:
            self.logger.error("Errors collecting data: %s", self.errors)

        if results:
            return pd.concat(results, ignore_index=True)
        else:
            return pd.DataFrame()

    def _add_columns(self, data: pd.DataFrame, add_columns: list, station: Union[dict, pd.DataFrame] = None) -> pd.DataFrame:
        """Add columns to the DataFrame

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with the data
        add_columns : list
            List of columns to add to the DataFrame
        station : Union[dict, pd.Dataframe], optional
            Station information, by default None

        Returns
        -------
        pd.DataFrame
            DataFrame with the added columns
        """

        if not add_columns and "name" not in data.columns:
            add_columns = ["name"]
        if add_columns:
            if "merged_id" in add_columns and "station_id" not in data.columns:
                station = station[["name", "id"]]
                data = data.merge(station, how="left", on="name")
                data["station_id"] = data["id"]
                data.drop(columns="id", inplace=True)
            if "id" in add_columns and "station_id" not in data.columns:
                data["station_id"] = station["id"]
            if "name" in add_columns:
                data["name"] = station["name"]
        return data

    def _convert_to_gdf(self, data: pd.DataFrame, has_geom: bool = False) -> gpd.GeoDataFrame:
        """Convert the DataFrame to a GeoDataFrame

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with the data

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with the data
        """
        data = data.copy()
        if has_geom:
            data = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")
            data["latitude"] = data.geometry.y
            data["longitude"] = data.geometry.x
        else:
            data = gpd.GeoDataFrame(data, geometry=gpd.points_from_xy(data.longitude, data.latitude))
        data.set_crs(epsg=4326, inplace=True)
        data.to_crs(epsg=3857, inplace=True)
        return data

    def remove_dup_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """ Remove Duplicate Columns

        Remove duplicated columns from a pandas DataFrame.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame to remove duplicated columns.

        Returns
        -------
        pd.DataFrame
            DataFrame without duplicated columns
        """
        keep_names = set()
        keep_icols = list()
        for icol, name in enumerate(data.columns):
            if name not in keep_names:
                keep_names.add(name)
                keep_icols.append(icol)
        data = data.iloc[:, keep_icols]
        return data

    def convert_to_numeric(self, data: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to numeric

        Convert columns to numeric in a pandas DataFrame

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame to convert columns to numeric

        Returns
        -------
        pd.DataFrame
            DataFrame with columns converted to numeric
        """
        columns = data.columns
        for column in columns:
            if column not in ["date_time", "name", "data_type"]:
                data[column] = pd.to_numeric(data[column], errors="coerce")
        return data

    def create_driver(self) -> webdriver:
        """Create a Chrome webdriver

        Returns
        -------
        webdriver
            Chrome webdriver
        """
        options = Options()
        args=["-headless", "--no-sandbox", "--disable-dev-shm-usage"]
        # args = []
        preferences=[]
        options = def_args_prefs(options, args, preferences)
        driver = webdriver.Chrome(options=options)
        return driver
