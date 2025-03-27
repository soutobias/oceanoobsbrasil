""" Get data from the bathing water quality in São Paulo """
import datetime
import json
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from oceanobs.oceanobs import Oceanobs
from oceanobs.oceanobs_handler.db_handler import DbHandler


class WaterQualitySP(Oceanobs):
    """Get data from the bathing water quality in São Paulo"""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://arcgis.cetesb.sp.gov.br/server/rest/services/Hosted/Praias/FeatureServer/0/query"

    def get_stations(self) -> pd.DataFrame:
        """Get stations from the bathing water quality in São Paulo

        Returns
        -------
        pd.DataFrame
            The stations
        """
        stations = self._request_data()
        stations = self._prepare_stations(stations)
        return stations

    def get(self,
            stations: pd.DataFrame = None,
            add_columns: list = None,
            **kwargs) -> pd.DataFrame:
        """Get data from the bathing water quality in São Paulo"""

        data = self._request_data()
        data = data[["data_amostra_inicio", "name", "classificacao_texto"]]
        data.rename(columns={"data_amostra_inicio": "date_time", "classificacao_texto": "cleaning"}, inplace=True)
        data["date_time"] = pd.to_datetime(data["date_time"], unit="ms")
        data["cleaning"] = data["cleaning"].apply(lambda x: True if x == "Própria" else False)
        data = self._add_columns(data, add_columns, stations)
        return data

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
        stations.rename(columns={"id_praia": "identifier"}, inplace=True)
        stations = stations[["name", "identifier", "latitude", "longitude"]]
        stations = self._convert_to_gdf(stations)
        return stations

    def _request_data(self) -> pd.DataFrame:
        """Request the data from the API

        Returns
        -------
        pd.DataFrame
            The data
        """
        params = {
            "f": "json",
            "cacheHint": "true",
            "resultOffset": "0",
            "resultRecordCount": "250",
            "where": "1=1",
            "orderByFields": "dist_norte ASC",
            "outFields": "*",
            "resultType": "standard",
            "returnGeometry": "true",
            "spatialRel": "esriSpatialRelIntersects",
        }

        response = requests.get(self.base_url, params=params)
        data = response.json()
        attributes = []
        for attribute in data["features"]:
            attribute["attributes"]["longitude"] = attribute["geometry"]["x"]
            attribute["attributes"]["latitude"] = attribute["geometry"]["y"]
            del attribute["geometry"]
            attributes.append(attribute["attributes"])
        data = pd.DataFrame(attributes)
        data["name"] = data["municipio"] + " - " + data["praia"]
        return data
