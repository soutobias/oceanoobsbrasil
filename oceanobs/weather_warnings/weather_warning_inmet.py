"""Weather Warning Inmet module"""

import json
from datetime import (
    datetime,
    timezone,
)

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import (
    shape,
)


class WeatherWarningInmet:
    """WeatherWarningInmet class"""

    def __init__(self, **kwargs):
        super().__init__()
        self.base_url = "https://apiprevmet3.inmet.gov.br/avisos/ativos"

    def get(self, **kwargs) -> pd.DataFrame:
        """Get the weather warnings from INMET website

        Returns
        -------
        pd.DataFrame
            The weather warnings
        """
        response = requests.get(self.base_url)
        if response.status_code != 200:
            self.logger.error("Error getting the weather warnings from %s", self.base_url)
            return
        try:
            data = response.json()
            today_futures = data.keys()
            params = []
            hour = (datetime.now(timezone.utc).hour // 6) * 6
            date_time = datetime.now(timezone.utc).replace(hour=hour)
            date_time = date_time.strftime(format="%Y-%m-%d %H:01:00")
            for today_future in today_futures:
                for weather_warning in data[today_future]:
                    param = {}
                    param["date_time"] = date_time
                    param["reference"] = today_future
                    param["start_date"] = weather_warning["inicio"]
                    param["end_date"] = weather_warning["fim"]
                    param["geometry"] = weather_warning["poligono"]
                    param["warning_type"] = weather_warning["descricao"]
                    param["warning_number"] = weather_warning["id_aviso"]
                    param["link"] = f"https://alertas2.inmet.gov.br/{weather_warning['id']}"
                    param["description"] = weather_warning["severidade"] + ". " + "".join(weather_warning["riscos"])
                    params.append(param)
            data = pd.DataFrame(params)
            data["start_date"] = pd.to_datetime(data["start_date"])
            data["end_date"] = pd.to_datetime(data["end_date"])
            data["geometry"] = data["geometry"].apply(lambda x: shape(json.loads(x)))
            data = gpd.GeoDataFrame(data, geometry="geometry")
            data.set_crs(epsg=4326, inplace=True)
            data.to_crs(epsg=3857, inplace=True)
        except Exception as e:
            self.logger.error("Error parsing the weather warnings from %s", self.base_url)
            self.logger.error(e)
            return
        return data
