"""Get data from the bathing water quality in Santa Catarina"""

import pandas as pd
import requests

from oceanobs.oceanobs import (
    Oceanobs,
)


class WaterQualitySC(Oceanobs):
    """Get data from the bathing water quality in Santa Catarina

    Parameters
    ----------
    base_url : str, optional
        Base URL for the data, by default None
    """

    def __init__(
        self,
        base_url: str = None,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://balneabilidade.ima.sc.gov.br/relatorio/mapa" if not base_url else base_url

    def get_stations(self) -> pd.DataFrame:
        """Get stations from the bathing water quality in São Paulo

        Returns
        -------
        pd.DataFrame
            The stations
        """
        stations = self._request_data()
        stations = pd.DataFrame(stations)
        stations = self._prepare_stations(stations)
        return stations

    def get(self, stations: pd.DataFrame = None, add_columns: list = None, **kwargs) -> pd.DataFrame:
        """Get data from the bathing water quality in São Paulo"""

        data = self._request_data()
        data = self._prepare_data(data)
        data["date_time"] = pd.to_datetime(data["date_time"], format="%d/%m/%Y")
        data = self._add_columns(data, add_columns, stations)
        return data

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
        stations["name"] = stations["MUNICIPIO"] + " - " + stations["PONTO_NOME"] + " - " + stations["BALNEARIO"]
        stations = stations[["CODIGO", "name", "LATITUDE", "LONGITUDE"]]
        stations.columns = ["identifier", "name", "latitude", "longitude"]
        stations = self._convert_to_gdf(stations)
        return stations

    def _request_data(self) -> pd.DataFrame:
        """Request the data from the API

        Returns
        -------
        pd.DataFrame
            The data
        """
        response = requests.post(self.base_url)
        data = response.json()
        return data

    def _prepare_data(self, data: dict) -> pd.DataFrame:
        """Prepare the data

        Parameters
        ----------
        data : dict
            The data

        Returns
        -------
        pd.DataFrame
            The prepared data
        """
        rows = []
        for station in data:
            for analysis in station["ANALISES"]:
                row = {
                    "identifier": station["CODIGO"],
                    "name": f"{station['MUNICIPIO']} - {station['PONTO_NOME']} - {station['BALNEARIO']}",
                    "date_time": analysis["DATA"],
                    "cleaning": False if analysis["CONDICAO"] == "IMPRÓPRIO" else True,
                }
                rows.append(row)

        data = pd.DataFrame(rows)
        return data
