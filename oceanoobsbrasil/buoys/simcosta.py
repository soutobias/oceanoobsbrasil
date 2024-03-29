import datetime
import json
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from oceanoobsbrasil.db import GetData


class Simcosta:
    def __init__(
        self,
        equip="buoy",
        start_date=str(int(np.ceil(time.time() - 3600 * 24))),
        end_date=str(int(np.ceil(time.time()))),
    ):
        # Connect to the database

        self.db = GetData()
        self.equip = equip
        self.start_date = start_date
        self.end_date = end_date
        self.stations = self.db.get(
            table="stations", institution=["=", "simcosta"], data_type=["=", self.equip]
        )

    def get(self, save_bd=True):
        for index, station in self.stations.iterrows():
            print(station.url)
            if int(station.url) > 100:
                url_address = f"https://simcosta.furg.br/api/intrans_data?boiaID={station['url']}&type=json&time1={self.start_date}&time2={self.end_date}&params=H10,HAvg,Hsig,HM0,Avg_Wv_Dir,Hmax,ZCN,Tp5,Tz,TAvg,T10,Tsig,Avg_Wv_Spread,Tp,Avg_Sal,Avg_W_Tmp1,Avg_W_Tmp2,Avg_Chl,Avg_Turb,Avg_Wnd_Dir_N,Gust_Sp,Avg_Dew,Avg_Air_Press,Avg_Sol_Rad,Avg_Air_Tmp,Avg_Hmt,Avg_Hmt,Avg_Wnd_Sp"
                print(url_address)
                with urllib.request.urlopen(url_address) as url:
                    data = json.loads(url.read().decode())
                    self.data = pd.DataFrame(data)

                self.result = self.data

                self.remove_dup_columns()

                if len(self.result) == 0:
                    print("Nao ha dados para essa boia")
                else:
                    self.result["date_time"] = pd.to_datetime(self.result.timestamp)
                    if int(station.url) > 300:
                        self.result = self.result[
                            [
                                "Avg_Air_Press",
                                "Avg_Air_Tmp",
                                "Avg_Hmt",
                                "Avg_Dew",
                                "Avg_Wnd_Sp",
                                "Avg_Wnd_Dir_N",
                                "Gust_Sp",
                                "Hsig",
                                "Hmax",
                                "Tp",
                                "Avg_W_Tmp1",
                                "Avg_Wv_Spread",
                                "Avg_Wv_Dir",
                                "date_time",
                            ]
                        ]
                        self.result.columns = [
                            "pres",
                            "atmp",
                            "rh",
                            "dewpt",
                            "wspd",
                            "wdir",
                            "gust",
                            "swvht",
                            "mxwvht",
                            "tp",
                            "sst",
                            "wvspread",
                            "wvdir",
                            "date_time",
                        ]
                    else:
                        self.result = self.result[["Avg_W_Tmp1", "date_time"]]
                        self.result.columns = ["atmp", "date_time"]

                    self.result = self.result.replace(
                        to_replace=["None", "NULL", " ", ""], value=np.nan
                    )
                    if save_bd:
                        self.result["station_id"] = str(station["id"])
                        self.db.feed_bd(table="data_stations", df=self.result)
                        print("ok")
                    else:
                        return self.result

            else:
                url_address = f"http://simcosta.furg.br/api/metereo_data?boiaID={station['url']}&type=json&time1={self.start_date}&time2={self.end_date}&params=Average_wind_direction_N,Last_sampling_interval_gust_speed,Average_Dew_Point,Average_Pressure,Solar_Radiation_Average_Reading,Average_Air_Temperature,Instantaneous_Humidity,Average_Humidity,Average_wind_speed"
                with urllib.request.urlopen(url_address) as url:
                    data = json.loads(url.read().decode())
                    self.data = pd.DataFrame(data)
                url_address = f"http://simcosta.furg.br/api/oceanic_data?boiaID={station['url']}&type=json&time1={self.start_date}&time2={self.end_date}&params=H10,HAvg,Hsig_Significant_Wave_Height_m,HM0,Mean_Wave_Direction_deg,Hmax_Maximum_Wave_Height_m,ZCN,Tp5,TAvg,T10,Tsig,Mean_Spread_deg,TP_Peak_Period_seconds,Average_Salinity,Average_Temperature_deg_C,Average_Temperature_C,Average_CDOM_QSDE,Average_Chlorophyll_Fluorescence,Average_Dissolved_Oxygen,Average_Nephelometric_Turbidity_Unit_NTU,Cell_Average_Direction_N,Cell_Average_Magnitude_mm_s"

                with urllib.request.urlopen(url_address) as url:
                    data1 = json.loads(url.read().decode())
                    self.data1 = pd.DataFrame(data1)

                self.result = pd.concat([self.data, self.data1], axis=1, join="inner")

                self.remove_dup_columns()

                if len(self.result) == 0:
                    print("Nao ha dados para essa boia")
                else:
                    self.result["date_time"] = pd.to_datetime(self.result.iloc[:, 0:6])
                    columns = [
                        "YEAR",
                        "MONTH",
                        "DAY",
                        "HOUR",
                        "MINUTE",
                        "SECOND",
                        "Hmt",
                        "Avg_Wnd_Dir",
                        "M_Decl",
                        "Avg_W_Tmp1",
                        "Avg_Sal",
                        "Avg_Spre_N",
                        "Avg_Wv_Dir",
                        "Avg_Cel1_Mag",
                        "Avg_Cel1_Dir",
                        "Avg_Cel1_Dir_N",
                        "Avg_Turb",
                        "Avg_Chl",
                        "Avg_DO",
                        "ZCN",
                        "HM0",
                        "TAvg",
                        "Tp5",
                        "T10",
                        "HAvg",
                        "Tsig",
                        "CDOM",
                        "H10",
                        "Avg_Sol_Rad",
                    ]

                    self.result.drop(columns=columns, inplace=True)

                    self.result.columns = [
                        "pres",
                        "atmp",
                        "rh",
                        "dewpt",
                        "wspd",
                        "wdir",
                        "gust",
                        "swvht",
                        "mxwvht",
                        "tp",
                        "sst",
                        "wvspread",
                        "wvdir",
                        "date_time",
                    ]

                    self.result = self.result.replace(
                        to_replace=["None", "NULL", " ", ""], value=np.nan
                    )
                    if save_bd:
                        self.result["station_id"] = str(station["id"])
                        self.db.feed_bd(table="data_stations", df=self.result)
                        print("ok")

                    else:
                        return self.result

    def remove_dup_columns(self):
        keep_names = set()
        keep_icols = list()
        for icol, name in enumerate(self.result.columns):
            if name not in keep_names:
                keep_names.add(name)
                keep_icols.append(icol)
        self.result = self.result.iloc[:, keep_icols]


if __name__ == "__main__":
    Simcosta().get(save_bd=True)
