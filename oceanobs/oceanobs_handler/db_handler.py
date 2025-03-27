"""Database handler module."""
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text

load_dotenv()
class DbHandler:
    """Database handler class"""

    def __init__(self):
        self.engine = DbHandler.engine_create()


    def get(self,
            table: str,
            columns: str = None,
            start_date: str = None,
            end_date: str = None,
            last: str = None,
            join: dict = None,
            query_kwargs=None) -> pd.DataFrame:
        """Get data from the database

        Parameters
        ----------
        table : str
            The table name
        columns : str, optional
            The columns to get, by default None
        start_date : str, optional
            The start date, by default None
        end_date : str, optional
            The end date, by default None
        last : str, optional
            The last date, by default None
        join : dict, optional
            The join tables, by default None
        query_kwargs : dict, optional
            The query kwargs, by default None

        Returns
        -------
        pd.DataFrame
            The data
        """
        join_string = ""
        if join:
            for table_join, column_join in join.items():
                join_string += f" JOIN {table_join} ON {table_join}.id = {table}.{column_join}"
        if table not in["stations" , "institutions", "station_types", "metarea_polygons"]:
            if last:
                query = f"SELECT * FROM {table} {join_string} WHERE station_id = {last} ORDER BY date_time DESC LIMIT 1"
            else:
                if start_date == None:
                    start_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime(
                        "%Y-%m-%d"
                    )
                if end_date == None:
                    end_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    )

                query = f"SELECT * FROM {table} {join_string} WHERE date_time > '{start_date}' AND date_time < '{end_date}'"

        else:
            query = f"SELECT * FROM {table} {join_string} WHERE true"

        if query_kwargs:
            query = self.create_query(query, query_kwargs)

        if columns:
            query = query.replace("*", columns)

        data = pd.read_sql(query, self.engine)

        return data

    def put(self, table: str, where_data: list, **kwargs) -> None:
        """Update data in the database

        Parameters
        ----------
        table : str
            The table name
        where_data : list
            The where data
        kwargs : dict
            The data to update
        """
        query = f"UPDATE {table} SET"
        for column, value in kwargs.items():
            query += f" {column} = '{value}',"
        query = query[:-1]
        query += f" WHERE {where_data[0]} = '{where_data[1]}'"
        with self.engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(query))
            transaction.commit()

    def post(self, table: str, data: pd.DataFrame) -> None:
        """Post data to the database

        Parameters
        ----------
        table : str
            The table name
        data : pd.DataFrame
            The data
        data_type : str, optional
            The data type, by default None
        """
        if "position" in data.columns or "geometry" in data.columns:
            data.to_postgis(name=table, con=self.engine, if_exists="append")
        else:
            data.to_sql(con=self.engine, name=table, if_exists="append", index=False)

    def delete(self, table: str, **kwargs) -> None:
        """Delete data from the database

        Parameters
        ----------
        table : str
            The table name
        kwargs : dict
            The query kwargs
        """
        query = f"DELETE FROM {table} WHERE true"
        if kwargs:
            query = self.create_query(query, kwargs)

        with self.engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(query))
            transaction.commit()

    def feed_bd(self, table: str, data: pd.DataFrame) -> None:
        """Feed the database

        Parameters
        ----------
        table : str
            The table name
        data : pd.DataFrame
            The data
        """
        if table == "data_stations":
            station = list(data.station_id.astype("str").unique())
            self.delete(
                table=table,
                station_id=["in", station],
                date_time=[">=", data["date_time"].min()],
            )

        elif table == "data_no_stations":
            institution = list(data.institution_id.unique())
            station_type = list(data.station_type_id.unique())
            self.delete(
                table=table,
                institution_id=["in", institution],
                station_type_id=["in", station_type],
                date_time=[">=", data["date_time"].min()],
            )
        elif table == "weather_warnings":
            self.delete(table=table, date_time=[">=", data["date_time"].min()], institution_id=["=", data["institution_id"].unique()[0]])

        elif table == "images":
            self.delete(table=table, file_name=["=", data["file_name"]])
        self.post(table=table, data=data)

    def get_columns(self, table: str) -> pd.DataFrame:
        """Get columns from the database

        Parameters
        ----------
        table : str
            The table name

        Returns
        -------
        pd.DataFrame
            The columns
        """
        query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
        columns = pd.read_sql(query, self.engine)
        return columns

    def engine_create() -> object:
        """Create the database engine

        Returns
        -------
        object
            The database engine
        """
        password = os.getenv("POSTGRE_PWD")

        local = os.getenv("POSTGRE_LOCAL")
        port = os.getenv("POSTGRE_PORT")

        if port:
            local = f"{local}:{port}"

        engine = create_engine(
            f"postgresql+psycopg2://{os.getenv('POSTGRE_USER')}:{password}@{local}/{os.getenv('POSTGRE_BD')}"
        )

        return engine

    def create_query(self, query: str, query_kwargs: dict) -> str:
        """Create a query

        Parameters
        ----------
        query : str
            The query
        query_kwargs : dict
            The query kwargs

        Returns
        -------
        str
            The query
        """
        for key, value in query_kwargs.items():
            if type(value[1]) == list:
                if len(value[1]) == 1:
                    query += f" AND {key} {value[0]} ('{value[1][0]}')"
                else:
                    query += f" AND {key} {value[0]} {tuple(value[1])}"
            else:
                query += f" AND {key} {value[0]} '{value[1]}'"

        return query
