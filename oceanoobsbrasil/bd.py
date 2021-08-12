from sqlalchemy import create_engine
import sqlalchemy
import pandas as pd
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

class Getdata():

    load_dotenv()

    def __init__(self):
        # Connect to the database
        self.engine = Getdata.engine_create()

    def get(self, table, start_date=None, end_date=None, **kwargs):

        if table != 'stations':
            if start_date == None:
                start_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d')
            if end_date == None:
                end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')

        query = f"SELECT * FROM {table} WHERE start_date > {start_date} AND end_date < {end_date}"

        if kwargs:
            for key, value in kwargs.items():
                query += f" AND {key} {value[0]} {value[1]}"

        df = pd.read_sql(query, self.engine)

        return df


    def post(self,table, df):

        if table!='stations':
            institution = df['institution'][0]
            self.delete(table=table, institution=['=',institution], date_time=['>', df['date_time'].min()])
            df.to_sql(con=self.engine, name=table, if_exists='append', index=False)

        return data

    def delete(self, table, **kwargs):

        query = "DELETE FROM data_stations WHERE"
        if kwargs:
            for key, value in kwargs.items():
                query += f"{key}{value[0]}{value[1]} AND"

        query = query[0:-4]

        cur = con.connect()

        cur.execute(query)

        print("deleted old data")


    def engine_create():

        engine = create_engine(f"postgresql+psycopg2://{os.getenv('POSTGRE_USER')}:{os.getenv('POSTGRE_PWD')}@{os.getenv('POSTGRE_LOCAL')}/{os.getenv('POSTGRE_BD')}")

        return engine
