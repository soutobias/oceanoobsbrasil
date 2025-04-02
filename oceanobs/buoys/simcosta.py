"""SIMCOSTA class"""

import time
from datetime import (
    datetime,
)

import numpy as np
import pandas as pd
import requests

from oceanobs.oceanobs import (
    Oceanobs,
)


# pd.set_option('future.no_silent_downcasting', True)
class Simcosta(Oceanobs):
    """Simcosta class

    This class is used to download data from SIMCOSTA buoys.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    base_url : str, optional
        Base URL for the data, by default
    """

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        n_workers: int = 1,
        base_url: str = None,
    ):
        super().__init__(start_date=start_date, end_date=end_date, n_workers=n_workers)
        self.start_date = self._validate_date(start_date, is_start_date=True)
        self.end_date = self._validate_date(end_date, is_start_date=False)
        self.station_type = "Buoy"
        self.base_url = "https://simcosta.furg.br/api" if not base_url else base_url

    def get_stations(self) -> pd.DataFrame:
        """Get the stations metadata

        Returns
        -------
        pd.DataFrame
            The stations metadata
        """
        url_address = self.base_url + "/equipamentos/all/toInformations"
        response = requests.get(url_address)
        if response.status_code != 200:
            self.logger.error("Error getting stations from %s", url_address)
            return
        stations = response.json()
        stations = pd.DataFrame(stations)
        stations = self._prepare_stations(stations)

        return stations

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
        date_str = int(time.mktime(datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").timetuple()))
        return date_str

    def _prepare_stations(self, stations: pd.DataFrame) -> pd.DataFrame:
        """Prepare the stations metadata

        Parameters
        ----------
        stations : pd.DataFrame
            The stations metadata

        Returns
        -------
        pd.DataFrame
            The prepared stations metadata
        """

        stations = stations[stations["tipo"].isin([1, 2, 5, 7])]
        stations = stations.copy()
        stations["type"] = stations["tipo"].apply(lambda x: "Tide Gauge" if x == 2 else "Buoy")
        df_stations = stations.copy()[["id", "titulo", "latitude", "longitude", "type"]]
        gdf_stations = self._convert_to_gdf(df_stations)
        gdf_stations.rename(columns={"id": "identifier"}, inplace=True)
        gdf_stations.rename(columns={"titulo": "name"}, inplace=True)
        gdf_stations["identifier"] = gdf_stations["identifier"].astype(str)

        if self.station_type:
            gdf_stations = gdf_stations[gdf_stations["type"] == self.station_type]

        gdf_stations.drop(columns=["type"], inplace=True)
        return gdf_stations

    def get_data(self, station, start_date=None, end_date=None, add_columns: list = None) -> tuple:
        """Get data from a station

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
        station.loc["identifier"] = int(station["identifier"])
        urls = self._get_api_urls(station)
        data = pd.DataFrame()
        for url in urls:
            url_address = url.replace("{{station_id}}", str(station["identifier"]))
            url_address = url_address.replace("{{start_date}}", str(self.start_date))
            url_address = url_address.replace("{{end_date}}", str(self.end_date))
            response = requests.get(url_address)
            if response.status_code != 200:
                error = f"No data for {station['name']}"
                return None, error
            json_data = response.json()
            data = pd.concat([data, pd.DataFrame(json_data)])
            if len(data) == 0:
                error = f"No data for {station['name']}"
                return None, error
        if data.empty:
            error = f"No data for {station['name']}"
            return None, error

        data = self._rename_columns(data)
        data = self._prepare_data(data)
        data["identifier"] = station["identifier"]
        data = self.remove_dup_columns(data)
        data = self._add_columns(data, add_columns, station)

        return data, None

    def _get_api_urls(self, station: pd.Series) -> list:
        """Get the API urls

        Parameters
        ----------
        station : pd.Series
            The station information

        Returns
        -------
        list
            The API urls
        """
        if self.station_type == "Tide Gauge":
            params = [
                "avg_rain_acc",
                "wind_speed",
                "Avg_Wnd_Sp",
                "wind_direction_n",
                "Avg_Wnd_Dir_N",
                "air_temp",
                "Avg_Air_Tmp",
                "relative_humidity",
                "Avg_Hmt",
                "dew_point",
                "Avg_Dew",
                "atm_pressure",
                "Avg_Air_Press",
                "water_l1",
                "avg_water_l1",
                "water_l1_ibge",
                "avg_water_l1_ibge",
                "water_l1_dhn",
                "avg_water_l1_dhn",
            ]
            urls = [
                self.base_url + "/intrans_data?boiaID={{station_id}}&type=json&time1={{start_date}}&time2={{end_date}}&params=" + ",".join(params),
            ]
        elif station["identifier"] > 100:
            params = [
                "H10",
                "HAvg",
                "Hsig",
                "HM0",
                "Avg_Wv_Dir",
                "Hmax",
                "ZCN",
                "Tp5",
                "Tz",
                "TAvg",
                "T10",
                "Tsig",
                "Avg_Wv_Spread",
                "Tp",
                "Avg_Sal",
                "Avg_W_Tmp1",
                "Avg_W_Tmp2",
                "Avg_Chl",
                "Avg_Turb",
                "Avg_Wnd_Dir_N",
                "Gust_Sp",
                "Avg_Dew",
                "Avg_Air_Press",
                "Avg_Sol_Rad",
                "Avg_Air_Tmp",
                "Avg_Hmt",
                "Avg_Hmt",
                "Avg_Wnd_Sp",
            ]
            urls = [
                self.base_url + "/intrans_data?boiaID={{station_id}}&type=json&time1={{start_date}}&time2={{end_date}}&params=" + ",".join(params),
            ]
        else:
            params = [
                "Average_wind_direction_N",
                "Last_sampling_interval_gust_speed",
                "Average_Dew_Point",
                "Average_Pressure",
                "Solar_Radiation_Average_Reading",
                "Average_Air_Temperature",
                "Instantaneous_Humidity",
                "Average_Humidity",
                "Average_wind_speed",
            ]
            params2 = [
                "H10",
                "HAvg",
                "Hsig_Significant_Wave_Height_m",
                "HM0",
                "Mean_Wave_Direction_deg",
                "Hmax_Maximum_Wave_Height_m",
                "ZCN",
                "Tp5",
                "TAvg",
                "T10",
                "Tsig",
                "Mean_Spread_deg",
                "TP_Peak_Period_seconds",
                "Average_Salinity",
                "Average_Temperature_deg_C",
                "Average_Temperature_C",
                "Average_CDOM_QSDE",
                "Average_Chlorophyll_Fluorescence",
                "Average_Dissolved_Oxygen",
                "Average_Nephelometric_Turbidity_Unit_NTU",
                "Cell_Average_Direction_N",
                "Cell_Average_Magnitude_mm_s",
            ]
            urls = [
                self.base_url + "/metereo_data?boiaID={{station_id}}&type=json&time1={{start_date}}&time2={{end_date}}&params=" + ",".join(params),
                self.base_url + "/oceanic_data?boiaID={{station_id}}&type=json&time1={{start_date}}&time2={{end_date}}&params=" + ",".join(params2),
            ]
        return urls

    def _rename_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Rename columns

        Parameters
        ----------
        data : pd.DataFrame
            Data to rename columns

        Returns
        -------
        pd.DataFrame
            The data with renamed columns
        """
        columns_to_rename = {
            "timestamp": "date_time",
            "Avg_Turb": "turb",
            "Avg_Chl": "chl",
            "Avg_Dew": "dewpt",
            "Avg_Hmt": "rh",
            "Avg_Air_Tmp": "atmp",
            "Avg_Air_Press": "pres",
            "Gust_Sp": "gust",
            "Avg_Wnd_Sp": "wspd",
            "Avg_Wnd_Dir_N": "wdir",
            "Avg_Sol_Rad": "srad",
            "Hsig": "swvht",
            "Tp": "tp",
            "Hmax": "mxwvht",
            "Havg": "whgt",
            "Tavg": "sst",
            "H10": "h10",
            "T10": "t10",
            "Avg_Wv_Dir": "wvdir_mag",
            "Avg_Wv_Spread": "wvspread_mag",
            "Tsig": "tsig",
            "Tp5": "tp5",
            "HM0": "hm0",
            "ZCN": "zcn",
            "Avg_Sal": "sal",
            "Avg_W_Tmp1": "wtmp",
            "Avg_W_Tmp2": "wtmp2",
            "Hmt": "hmt",
            "Avg_Wnd_Dir": "wdir_mag",
            "M_Decl": "mdecl",
            "C_Avg_Dir_N": "cdir",
            "C_Avg_Spd": "cspd",
            "C_Avg_Dir": "cdir_mag",
            "Avg_Wv_Spread_N": "wvspread",
            "Avg_Wv_Dir_N": "wvdir",
            "wind_speed": "",
            "air_temp": "",
            "relative_humidity": "",
            "water_l1": "water_level",
        }
        for key, value in columns_to_rename.items():
            if key in data.columns:
                data.rename(columns={key: value}, inplace=True)
        if "date_time" not in data.columns:
            data["date_time"] = (
                data["YEAR"].astype(str)
                + "-"
                + data["MONTH"].astype(str).str.zfill(2)
                + "-"
                + data["DAY"].astype(str).str.zfill(2)
                + " "
                + data["HOUR"].astype(str).str.zfill(2)
                + ":"
                + data["MINUTE"].astype(str).str.zfill(2)
                + ":"
                + data["SECOND"].astype(str).str.zfill(2)
                + "+00:00"
            )
        data["date_time"] = pd.to_datetime(data["date_time"])
        data.drop(columns=["YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND"], inplace=True)

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
        data = data.infer_objects(copy=False)
        data = data.replace(to_replace=["None", None, "NULL", " ", ""], value=np.nan)
        float_columns = [
            "turb",
            "chl",
            "dewpt",
            "rh",
            "atmp",
            "pres",
            "gust",
            "wspd",
            "wdir",
            "srad",
            "swvht",
            "tp",
            "mxwvht",
            "whgt",
            "sst",
            "h10",
            "t10",
            "wvdir",
            "wvspread",
            "tsig",
            "tp5",
            "hm0",
            "zcn",
            "sal",
            "wtmp",
            "wtmp2",
            "hmt",
            "cdir",
            "cspd",
            "wvspread",
            "wvdir",
        ]
        for column in float_columns:
            if column in data.columns:
                if isinstance(data[column], (pd.Series, list, tuple, np.ndarray)):
                    data[column] = pd.to_numeric(data[column], errors="coerce")
                else:
                    print(f"Warning: Column {data[column]} is not a valid 1D array or Series.")
        return data
