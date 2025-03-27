"""Aqualink buoy module"""
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point

from oceanobs.oceanobs import Oceanobs

class AqualinkBuoy(Oceanobs):
    """Get data from Aqualink buoy

    This class is used to get data from Aqualink buoy.

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
        **kwargs
    ):

        super().__init__(start_date=start_date,
                         end_date=end_date,
                         n_workers=n_workers)
        self.start_date = self._validate_date(start_date, is_start_date=True)
        self.end_date = self._validate_date(end_date, is_start_date=False)
        self.base_url = "https://ocean-systems.uc.r.appspot.com/api"

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
        date_str = date_str + ".000Z"
        return date_str

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Aqualink buoy

        Returns
        -------
        pd.DataFrame
            The stations
        """
        url_address = self.base_url + "/sites"
        response = requests.get(url_address)
        if response.status_code != 200:
            self.logger.error("Error getting stations from %s", url_address)
            return
        stations = response.json()
        stations = pd.DataFrame(stations)
        stations = stations[stations["sensorId"].str.contains("SPOT", na=False)]
        stations = stations[stations["status"] == "deployed"]

        stations = self._prepare_stations(stations)

        return stations

    def _prepare_stations(self, stations: pd.DataFrame) -> pd.DataFrame:
        """ Prepare the stations metadata

        Parameters
        ----------
        stations : pd.DataFrame
            The stations metadata

        Returns
        -------
        pd.DataFrame
            The prepared stations metadata
        """
        df_stations = stations.copy()[["id", "name", "polygon"]]
        df_stations["geometry"] = df_stations["polygon"].apply(lambda x: Point(x["coordinates"]))
        df_stations = df_stations.drop(columns=["polygon"])
        gdf_stations = self._convert_to_gdf(df_stations, has_geom="geometry")
        gdf_stations.rename(columns={"id": "identifier"}, inplace=True)
        gdf_stations["identifier"] = gdf_stations["identifier"].astype(str)

        return gdf_stations

    def get_data(self,
                 station,
                 start_date=None,
                 end_date=None,
                 add_columns: list = None
                 ) -> tuple:
        """ Get data from a station

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
        url_address = self.base_url + f"/time-series/sites/{station['identifier']}?start={self.start_date}&end={self.end_date}&metrics=bottom_temperature,top_temperature,wind_speed,significant_wave_height,barometric_pressure_top,barometric_pressure_bottom,surface_temperature&hourly=true"
        self.logger.info("Getting data from %s", url_address)
        response = requests.get(url_address)
        if response.status_code != 200:
            error = f"No data for {station['name']}"
            return None, error
        json_data = response.json()
        data = None
        for key in json_data.keys():
            var_df = pd.DataFrame(json_data[key][0]["data"])
            var_df.columns = [key, "date_time"]
            if data is None:
                data = var_df
            else:
                if var_df.empty:
                    continue
                data = pd.merge(data, var_df, on="date_time", how="outer")
        if data is None:
            error = f"No data for {station['name']}"
            return None, error
        data = self._rename_columns(data)
        data["date_time"] = pd.to_datetime(data["date_time"])

        if add_columns:
            if "id" in add_columns:
                data["station_id"] = station["id"]

        return data, None

    def _rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename the columns of the DataFrame

        Parameters
        ----------
        data : pd.DataFrame
            The DataFrame with the data

        Returns
        -------
        pd.DataFrame
            The DataFrame with the renamed columns
        """

        data.rename(columns={"top_temperature": "sst"}, inplace=True)
        data.rename(columns={"significant_wave_height": "swvht"}, inplace=True)
        data.rename(columns={"wind_speed": "wspd"}, inplace=True)
        if "barometric_pressure_top" in data.columns:
            data.rename(columns={"barometric_pressure_top": "pres"}, inplace=True)
        return data
