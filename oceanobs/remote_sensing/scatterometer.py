from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
from tqdm import tqdm
import xarray as xr
from dotenv import load_dotenv
from harmony import BBox, Client, Collection, Request

from oceanobs.oceanobs import Oceanobs

load_dotenv()


class Scatterometer(Oceanobs):
    """Scatterometer data collection class


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

    def __init__(
        self,
        collections=["C2075141559-POCLOUD"],
        start_date: str = None,
        end_date: str = None,
        lat_lon_limits: dict = None,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            lat_lon_limits=lat_lon_limits,
            n_workers=n_workers,
        )
        self.start_date = self._validate_date(start_date, is_start_date=True)
        self.end_date = self._validate_date(end_date, is_start_date=False)
        self.collections = collections
        self._username = os.getenv("EDL_USR")
        self._password = os.getenv("EDL_PWD")
        if not self._username or not self._password:
            raise ValueError("Username and password must be set")

    def get(self) -> pd.DataFrame:
        """Get the data from Scatterometers

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """
        wind_flag, wind_dir, wind_speed, wind_time, wind_lat, wind_lon = (
            [],
            [],
            [],
            [],
            [],
            [],
        )
        for collection in self.collections:
            nc_files = self.download(collection)
            with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
                futures = [
                    executor.submit(
                        self.get_data,
                        file=file,
                        wind_flag=wind_flag,
                        wind_dir=wind_dir,
                        wind_speed=wind_speed,
                        wind_time=wind_time,
                        wind_lat=wind_lat,
                        wind_lon=wind_lon,
                    )
                    for file in nc_files
                ]
                for future in tqdm(as_completed(futures), desc="Downloading data", total=len(futures)):
                    future.result()
        date_time = np.concatenate(wind_time)
        wdir = np.concatenate(wind_dir)
        wspd = np.concatenate(wind_speed)
        lat = np.concatenate(wind_lat)
        lon = np.concatenate(wind_lon)
        win_flag = np.concatenate(wind_flag)

        # Create final DataFrame
        data = pd.DataFrame(
            {
                "date_time": date_time,
                "latitude": lat,
                "longitude": lon,
                "wdir": wdir,
                "wspd": wspd,
                "flag": win_flag,
            }
        )
        data = data.loc[data["date_time"].notna()]
        data = data.loc[data["latitude"].notna()]
        data = data.loc[data["longitude"].notna()]
        data = data.loc[data["flag"] == 0]
        data.drop(columns="flag", inplace=True)
        data.wspd = (data.wspd * 1.94384).round(decimals=1)
        data = data.replace(0, np.nan)
        data = self.convert_to_numeric(data)
        data["longitude"] = data["longitude"].apply(lambda x: x - 180 if x > 180 else x)
        data = self._convert_to_gdf(data)
        data["station_type"] = "Scatterometer"
        return data

    def get_data(
        self,
        file: str,
        wind_flag: list,
        wind_dir: list,
        wind_speed: list,
        wind_time: list,
        wind_lat: list,
        wind_lon: list,
    ):
        """Get the data from the Scatterometer

        Parameters
        ----------
        file : str
            URL of the file to download
        wind_flag : list
            List of wind quality flags
        wind_dir : list
            List of wind directions
        wind_speed : list
            List of wind speeds
        wind_time : list
            List of wind times
        wind_lat : list
            List of wind latitudes
        wind_lon : list
            List of wind longitudes
        """
        ds = xr.open_dataset(file)
        wind_flag.append(ds["wvc_quality_flag"].values.ravel())
        wind_dir.append(ds["wind_dir"].values.ravel())
        wind_speed.append(ds["wind_speed"].values.ravel())
        wind_time.append(ds["time"].values.ravel())
        wind_lat.append(ds["lat"].values.ravel())
        wind_lon.append(ds["lon"].values.ravel())
        os.remove(file)

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
        date_str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return date_str

    def download(self, collection):
        harmony_client = Client(auth=(self._username, self._password))
        collection_id = Collection(collection)

        request = Request(
            collection=collection_id,
            temporal={"start": self.start_date, "stop": self.end_date},
            spatial=BBox(
                self.lat_lon_limits["min_lon"],
                self.lat_lon_limits["min_lat"],
                self.lat_lon_limits["max_lon"],
                self.lat_lon_limits["max_lat"],
            ),
        )
        if request.is_valid():
            job_id = harmony_client.submit(request)
            self.logger.info(f"Job ID: {job_id}")
            harmony_client.result_json(job_id, show_progress=True)
            self.logger.info(f"Job ID: {job_id} completed")
        temp_dir = tempfile.mkdtemp()
        futures = harmony_client.download_all(job_id, directory=temp_dir, overwrite=True)
        nc_files = [f.result() for f in futures]
        return nc_files
