"""OceanobsHandler module"""
import json
import logging
from datetime import datetime, timedelta, timezone
import os
import pandas as pd
from dotenv import load_dotenv
from oceanobs.oceanobs_handler.db_handler import DbHandler
from oceanobs.oceanobs_handler.utils import DATA_METHODS

load_dotenv()
class OceanobsHandler:
    """OceanobsHandler class

    This class is used to handle the data collection from the stations.

    Parameters
    ----------
    method : str, optional
        Method to get the data, by default None
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    logger : logging.Logger, optional
        Logger, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    """
    def __init__(self,
                 method: str = None,
                 start_date: str = None,
                 end_date: str = None,
                 logger: logging.Logger = None,
                 n_workers: int = 1,
                 ):
        if not logger:
            self.logger = logging.getLogger(__name__)
        self.start_date = start_date
        self.end_date = end_date
        self.n_workers = n_workers
        self.db_handler = DbHandler()
        self.data_method = DATA_METHODS[method]
        institution = self.data_method["institution"]
        self.institution = self.db_handler.get(table="institutions",
                                               query_kwargs={"name": ["=", institution]}).iloc[0]["id"]
        self.data_type = self.data_method["data_type"]
        station_type = self.data_method.get("station_type")
        if station_type:
            self.station_type = self.db_handler.get(table="station_types",
                                                    query_kwargs={"station_type": ["=", station_type]}).iloc[0]["id"]
        self.class_instance = self.data_method["class_name"](start_date=self.start_date,
                                                             end_date=self.end_date,
                                                             n_workers=self.n_workers,
                                                             station_type=self.data_method.get("station_type"))

    def run_pipeline(self) -> pd.DataFrame:
        """Run the pipeline

        Run the pipeline to get data from the stations and save it to the database.

        Returns
        -------
        pd.DataFrame
            The data
        """

        if self.data_type == "station":
            db_stations = self.get_db_stations()
            data_station = self.class_instance.get_stations()
            stations = self.update_db_stations(data_station, db_stations)
            if self.data_method.get("filter"):
                stations = self.filter_stations(stations, self.data_method["filter"])
            if self.data_method.get("get_all"):
                output_data = self.class_instance.get(stations, add_columns = ["merged_id"])
            else:
                output_data = self.class_instance.get(stations, add_columns = ["id"])
            output_data = self.remove_columns(output_data)
            table = "data_stations"
        elif self.data_type == "warning":
            output_data = self.class_instance.get()
            output_data["institution_id"] = self.institution
            if "region" in output_data.columns:
                metarea_id = self.db_handler.get(columns="id,name",
                                                table="metarea_polygons",
                                                query_kwargs={"name": ["in", list(output_data["region"].unique())]})
                output_data["metarea_polygon_id"] = output_data["region"].map(metarea_id.set_index("name")["id"])
                output_data.drop(columns=["region"], inplace=True)

            if "reference" in output_data.columns:
                output_data = output_data[output_data["reference"] == "hoje"]
                output_data.drop(columns=["reference"], inplace=True)
            table = "weather_warnings"
        elif self.data_type == "nostation":
            output_data = self.class_instance.get()
            output_data.rename(columns={"identifier": "station_identifier"}, inplace=True)
            output_data["station_type_id"] = self.station_type
            output_data["institution_id"] = self.institution
            output_data.drop(columns=["station_type"], inplace=True)
            table = "data_no_stations"

        self.save_db(output_data, table)

        return output_data


    def get_db_stations(self) -> pd.DataFrame:
        """Get stations from the database

        Returns
        -------
        pd.DataFrame
            The stations
        """
        query_kwargs = {
            "institution_id": ["=", self.institution],
            "station_type_id": ["=", self.station_type]
            }
        if "name" in self.data_method:
            query_kwargs["name"] = ["=", self.data_method["name"]]

        stations = self.db_handler.get(table="stations",
                                       query_kwargs=query_kwargs)

        return stations

    def update_db_stations(self,
                           data_stations: pd.DataFrame,
                           db_stations: pd.DataFrame) -> pd.DataFrame:
        """Update stations in the database

        Update stations in the database.

        Parameters
        ----------
        data_stations : pd.DataFrame
            Data stations
        db_stations : pd.DataFrame
            Database stations

        Returns
        -------
        pd.DataFrame
            The updated stations
        """
        changes_in_db_stations = False
        for station in data_stations.iterrows():
            station = station[1]
            db_station = db_stations[db_stations["identifier"] == station["identifier"]]
            if len(db_station) == 0:
                continue
            db_station = db_station.iloc[0]
            if float(db_station["latitude"]) != float(station["latitude"]) or float(db_station["longitude"]) != float(station["longitude"]):
                changes_in_db_stations = True
                self.logger.info("Updating station %s", station["identifier"])
                self.db_handler.put(table="stations",
                                    where_data=["identifier",
                                    station["identifier"]],
                                    geometry=station["geometry"],
                                    latitude=station["latitude"],
                                    longitude=station["longitude"])
        # Remove stations that are already in the database
        stations = data_stations[~data_stations["identifier"].isin(db_stations["identifier"])]
        stations["institution_id"] = self.institution
        stations["station_type_id"] = self.station_type

        if len(stations) > 0:
            changes_in_db_stations = True
            stations.to_postgis(name="stations", con=self.db_handler.engine, if_exists="append")
        if changes_in_db_stations:
            return self.get_db_stations()
        else:
            return db_stations

    def save_db(self,
                data: pd.DataFrame,
                table: str) -> None:
        """ Save data to the database

        Save data to the database.

        Parameters
        ----------
        data : pd.DataFrame
            Data to save to the database
        table : str
            Table name

        Returns
        -------
        None
        """
        self.db_handler.feed_bd(table=table, data=data)

    def remove_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove columns from the data

        Remove columns from the data that are not in the database.

        Parameters
        ----------
        data : pd.DataFrame
            Data to remove columns

        Returns
        -------
        pd.DataFrame
            Data without the columns
        """
        columns = self.db_handler.get_columns("data_stations")
        columns = columns["column_name"].tolist()
        data = data[[col for col in data.columns if col in columns]]
        return data

    def filter_stations(self, stations: pd.DataFrame, filter_file: str) -> pd.DataFrame:
        """Filter stations

        Filter stations based on the station type.

        Parameters
        ----------
        stations : pd.DataFrame
            The stations
        filter_file : str
            The filter file

        Returns
        -------
        pd.DataFrame
            The filtered stations
        """
        filter_file = os.path.join(os.path.dirname(__file__), f"../data/{filter_file}")
        with open(filter_file, "r") as file:
            filter_data = json.load(file)
        stations = stations[stations["identifier"].isin(filter_data["identifiers"])]
        return stations
