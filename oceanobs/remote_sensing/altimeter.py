from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import glob
from io import BytesIO
import os
import re
from datetime import datetime
from tqdm import tqdm
import xarray as xr
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from netCDF4 import Dataset

from oceanobs.oceanobs import Oceanobs


class Altimeter(Oceanobs):
    """ OSMC data collection class


    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
    lat_lon_limits : dict, optional
        Latitude and longitude limits, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """
    def __init__(self,
                 start_date: str = None,
                 end_date: str = None,
                 lat_lon_limits: dict = None,
                 n_workers: int = 1,
                 **kwargs):
        super().__init__(start_date=start_date,
                         end_date=end_date,
                         lat_lon_limits=lat_lon_limits,
                         n_workers=n_workers)

        self.lat_lon_limits["min_lon"] += 180
        self.lat_lon_limits["max_lon"] += 180
        self.start_date = self._validate_date(start_date, is_start_date=True)
        self.end_date = self._validate_date(end_date, is_start_date=False)
        self.base_url = "https://www.ncei.noaa.gov/data/oceans/jason3/ogdr/ogdr/"

    def get(self) -> pd.DataFrame:
        """Get the data from the OSMC stations

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """
        files = self.get_nc_files()
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            futures = [
                executor.submit(partial(self.get_data, file=file))
                for file in files
            ]
            results = []
            for future in tqdm(as_completed(futures), desc="Downloading data", total=len(futures)):
                result = future.result()
                if result is not None:
                    results.append(result)
        data = pd.concat(results)
        data = self._convert_to_gdf(data)
        data["station_type"] = "Altimeter"
        return data

    def get_data(self, file: str) -> pd.DataFrame:
        """Get the data from the OSMC stations

        Parameters
        ----------
        file : str
            URL of the file to download

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """
        response = requests.get(file, stream=True)
        response.raise_for_status()
        with BytesIO(response.content) as file:
            ds = xr.load_dataset(file, engine="h5netcdf", group="data_01")
            ds_data = xr.load_dataset(file, engine="h5netcdf", group="data_01/ku")
        ds = xr.merge([ds, ds_data])
        ds = self._filter_data_based_on_lat_lon(ds)
        if len(ds.time.values) == 0:
            return
        data = {
            "date_time":ds["time"].values,
            "latitude": ds["latitude"].values,
            "longitude": ds["longitude"].values - 180,
            "wspd": ds["wind_speed_alt"].values,
            "swvht": ds["swh_ocean"].values,
            "flag": ds["swh_ocean_compression_qual"].values
        }
        data = pd.DataFrame(data)
        data["date_time"] = pd.to_datetime(data["date_time"])
        data = data[
            (data["wspd"] < 9999) & (data["swvht"] < 9999) &
            (data["wspd"] > 0) & (data["swvht"] > 0)
        ]
        data.wspd *= 1.94384
        data = data.drop(columns=["flag"])
        return data

    def _filter_data_based_on_lat_lon(self, ds: xr.Dataset) -> pd.DataFrame:
        """Filter the data based on the latitude and longitude limits

        Parameters
        ----------
        ds : xr.Dataset
            Dataset with the data

        Returns
        -------
        pd.DataFrame
            DataFrame with the filtered data
        """
        ds_subset = ds.where(
            (ds.latitude >= self.lat_lon_limits["min_lat"]) & (ds.latitude <= self.lat_lon_limits["max_lat"]) &
            (ds.longitude >= self.lat_lon_limits["min_lon"]) & (ds.longitude <= self.lat_lon_limits["max_lon"]),
            drop=True
        )
        return ds_subset

    def _validate_date(self, date_str: str = None, is_start_date: bool = True) -> str:
        """Validates the date format and returns a datetime object.

        Parameters
        ----------
        date_str : str, optional
            Date string to validate, by default None
        is_start_date : bool, optional
            If the date is the start date, by default True

        Returns
        -------
        str
            The validated date
        """
        date_str = super()._validate_date(date_str, is_start_date)
        date_str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").strftime("%Y%m%d")
        return date_str

    def get_nc_files(self):
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        cycles = [
            td.find("a").get("href")
            for td in soup.find_all("td")
            if td.find("a") and td.find("a").get("href").startswith("cycle")
        ]
        cycles.sort(reverse=True)
        pattern = re.compile("JA3_(.*)_(.*)_(.*)_(.*)_(.*)_(.*).nc")
        files = []
        for cycle in cycles:
            has_files = False
            cycle_url = self.base_url + cycle
            response = requests.get(cycle_url)
            soup = BeautifulSoup(response.text, "html.parser")
            cycle_files = [
                td.find("a").get("href")
                for td in soup.find_all("td")
                if td.find("a") and td.find("a").get("href").startswith("JA3_")
            ]
            for file in cycle_files:
                match = pattern.match(file)
                if match:
                    data_datetime = match.group(3)
                    if self.start_date < data_datetime < self.end_date:
                        has_files = True
                        file_url = cycle_url + file
                        files.append(file_url)
            if not has_files:
                break
        return files
