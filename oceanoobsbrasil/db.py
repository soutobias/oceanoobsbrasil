"""
Created on Tue Feb 12 23:34:44 2019
@author: tobia
"""

from sqlalchemy import create_engine
import sqlalchemy
import pandas as pd
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import urllib

class GetData():

    load_dotenv()

    def __init__(self):
        # Connect to the database
        self.engine = GetData.engine_create()

    def get(self, table, start_date=None, end_date=None, last=None, **kwargs):

        if table != 'stations':
            if last:
                query = f"SELECT * FROM {table} WHERE station_id = {last} ORDER BY date_time DESC LIMIT 1"
            else:
                if start_date == None:
                    start_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d')
                if end_date == None:
                    end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')

                query = f"SELECT * FROM {table} WHERE date_time > '{start_date}' AND date_time < '{end_date}'"

        else:
            query = f"SELECT * FROM {table} WHERE true"


        if kwargs:
            query = self.create_query(query, kwargs)

        df = pd.read_sql(query, self.engine)

        return df

    def post(self,table, df, data_type=None):

        if table == 'data_stations':
            station = list(df.station_id.astype('str').unique())
            self.delete(table=table, station_id=['in',station], date_time=['>=', df['date_time'].min()])

        elif table == 'data_no_stations':
            institution = list(df.institution.unique())
            self.delete(table=table, institution=['in', institution], data_type=['=', data_type], date_time=['>=', df['date_time'].min()])

        df.to_sql(con=self.engine, name=table, if_exists='append', index=False)

    def delete(self, table, **kwargs):

        query = f"DELETE FROM {table} WHERE true"
        if kwargs:
            query = self.create_query(query, kwargs)

        self.engine.execute(query)


    def feed_bd(self, table, df, data_type=None):
        self.post(table=table, df=df, data_type=data_type)


    def engine_create():

        password = urllib.parse.quote_plus(os.getenv('POSTGRE_PWD'))

        engine = create_engine(f"postgresql+psycopg2://{os.getenv('POSTGRE_USER')}:{password}@{os.getenv('POSTGRE_LOCAL')}/{os.getenv('POSTGRE_BD')}")

        return engine

    def create_query(self, query, kwargs):
        for key, value in kwargs.items():
            if type(value[1]) == list:
                if len(value[1]) == 1:
                    query += f" AND {key} {value[0]} ('{value[1][0]}')"
                else:
                    query += f" AND {key} {value[0]} {tuple(value[1])}"
            else:
                query += f" AND {key} {value[0]} '{value[1]}'"

        return query
