"""CHMTideTables class"""

import pandas as pd
import requests
from bs4 import (
    BeautifulSoup,
)

from oceanobs.oceanobs import (
    Oceanobs,
)


class CHMTideTables(Oceanobs):
    """CHMTideTables  class

    This class is used to get the links for the tide tables from CHM.

    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://www.marinha.mil.br/chm/tabuas-de-mare?page={page}"
        self.tide_table_url = "https://www.marinha.mil.br"

    def get_stations(self) -> pd.DataFrame:
        """Get stations from Pernambuco buoys

        The stations are read from a json file.

        Returns
        -------
        pd.DataFrame
            The stations
        """
        data = self.scrape_page()
        data = self._convert_to_gdf(data)
        data.drop(columns=["tide_table"], inplace=True)
        return data

    def get(self, add_columns: list = None) -> tuple:
        """Get the last available data from a station

        Parameters
        ----------
        station : dict
            Station information
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        tuple
            The data and the error message
        """
        data = self.scrape_page()
        data = self._add_columns(data, add_columns, data)
        data.drop(columns=["latitude", "longitude"], inplace=True)
        return data

    def scrape_page(self):
        names = []
        tide_tables = []
        latitudes = []
        longitudes = []
        for page in range(0, 3):
            base_url = self.base_url.format(page=page)
            print(base_url)
            response = requests.get(base_url, verify=False)
            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                name = table.find("td", {"class": "views-field views-field-title"})
                names.append(name.text.strip())
                tide_table = table.find("a")
                tide_tables.append(self.tide_table_url + tide_table.attrs["href"])
                position = table.find("td", {"class": "views-field views-field-field-localizacao"})
                position = position.text.replace("(", "").replace(")", "").split(" ")
                latitude = position[2]
                longitude = position[1]
                latitudes.append(float(latitude))
                longitudes.append(float(longitude))
        data = pd.DataFrame(
            {
                "name": names,
                "tide_table": tide_tables,
                "latitude": latitudes,
                "longitude": longitudes,
            }
        )
        return data
