import numpy as np
import pandas as pd
import requests

from oceanobs.oceanobs import (
    Oceanobs,
)


class OSMC(Oceanobs):
    """OSMC data collection class

    This class is used to collect data from the OSMC stations.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    lat_lon_limits : dict, optional
        Latitude and longitude limits, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    station_type : str, optional
        The type of station to be downloaded, by default None. It can be "drifter" or "float"
    base_url : str, optional
        Base URL for the data, by default None
    """

    def __init__(
        self,
        start_date: str = None,
        lat_lon_limits: dict = None,
        station_type: str = "drifter",
        base_url: str = None,
        **kwargs,
    ):
        super().__init__(start_date=start_date, lat_lon_limits=lat_lon_limits)
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = "http://osmc.noaa.gov/erddap/tabledap/OSMC_30day.htmlTable?platform_code,platform_type,time,latitude,longitude,observation_depth,sst,atmp,ztmp,slp,wvht"
        self.station_type = station_type
        if self.station_type not in ["drifter", "float"]:
            self.logger.error("Station type must be 'drifter' or 'float'")
            raise ValueError("Station type must be 'drifter' or 'float'")
        self.data_type = "DRIFTING BUOYS" if self.station_type == "drifter" else "PROFILING FLOATS AND GLIDERS"

    def get(self, **kwargs) -> pd.DataFrame:
        """Get the data from the OSMC stations

        Parameters
        ----------
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        pd.DataFrame
            DataFrame with the data
        """
        params = [
            f'platform_type="{self.data_type}"',
            f"time>={self.start_date}",
            f"latitude>={self.lat_lon_limits['min_lat']}",
            f"latitude<={self.lat_lon_limits['max_lat']}",
            f"longitude>={self.lat_lon_limits['min_lon']}",
            f"longitude<={self.lat_lon_limits['max_lon']}",
        ]
        url = self.base_url + "&" + "&".join(params)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Error getting data from OSMC: {e}")
            return
        try:
            data = pd.read_html(response.content)[1]
            data.columns = data.columns.droplevel(level=1)
        except Exception as e:
            self.logger.error(f"Error reading data from OSMC: {e}")
            return
        data.sst.fillna(data.ztmp.dropna(), inplace=True)
        data = data.loc[data["observation_depth"] >= -1]
        data = self._rename_columns(data)
        data = self._convert_to_gdf(data)
        data["date_time"] = pd.to_datetime(data["date_time"], format="%Y-%m-%dT%H:%M:%SZ")
        data.fillna(np.nan, inplace=True)
        # data = self._add_columns(data, add_columns)
        data["station_type"] = self.station_type
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
                "platform_code",
                "time",
                "latitude",
                "longitude",
                "sst",
                "atmp",
                "slp",
                "wvht",
            ]
        ]
        data.columns = [
            "identifier",
            "date_time",
            "latitude",
            "longitude",
            "sst",
            "atmp",
            "pres",
            "swvht",
        ]
        return data
