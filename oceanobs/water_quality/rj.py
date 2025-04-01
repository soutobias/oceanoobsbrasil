"""Get data from the bathing water quality in Rio de Janeiro"""

import time
from selenium.webdriver.common.by import By
import pandas as pd
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from oceanobs.oceanobs import Oceanobs
from oceanobs.utils.utils import quit_driver


class WaterQualityRJ(Oceanobs):
    """Get data from the bathing water quality in Rio de Janeiro"""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.code_url = "https://www.inea.rj.gov.br/ar-agua-e-solo/balneabilidade-das-praias/"
        self.base_url = "https://app.powerbi.com/view?r={code}&pageName=64fcd9486da0b10c1015#:~:text=Power%20BI%20Report&text=No%20entanto%2C%20se%20o%20%C3%BAltimo,classificado%20como%20impr%C3%B3prio%20para%20banho."
        self.data = None

    def get_stations(self) -> pd.DataFrame:
        """Get stations from the bathing water quality in São Paulo

        Returns
        -------
        pd.DataFrame
            The stations
        """
        data = self._scrape_page()
        data.drop(columns=["cleaning", "date_time"], inplace=True)
        data = self._convert_to_gdf(data)
        return data

    def get(self, stations: pd.DataFrame = None, add_columns: list = None, **kwargs) -> pd.DataFrame:
        """Get data from the bathing water quality in São Paulo"""

        data = self._scrape_page()
        data.drop(columns=["latitude", "longitude"], inplace=True)
        data["date_time"] = pd.to_datetime(data["date_time"], format="%m/%d/%Y")
        data["cleaning"] = data["cleaning"].apply(lambda x: False if x == "Imprópria" else True)
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
        stations.rename(columns={"id_praia": "identifier"}, inplace=True)
        stations = stations[["name", "identifier", "latitude", "longitude"]]
        stations = self._convert_to_gdf(stations)
        return stations

    def _scrape_page(self):
        if self.data:
            return self.data
        driver = self.create_driver()
        driver.get(self.base_url)
        time.sleep(30)
        elements = driver.find_elements(By.TAG_NAME, "visual-container")
        elements[8].find_element(By.TAG_NAME, "transform").click()
        time.sleep(5)
        all_elements = []
        elements = driver.find_elements(By.XPATH, "//div[@role='row']")
        all_elements = self._get_all_elements(elements, all_elements)
        for _ in range(1000):
            actions = ActionChains(driver)
            actions.move_to_element(elements[-1]).perform()
            actions.send_keys(Keys.PAGE_DOWN).perform()
            elements = driver.find_elements(By.XPATH, "//div[@role='row']")
            if elements[-1].text == all_elements[-1]:
                break
            all_elements = self._get_all_elements(elements, all_elements)

        quit_driver(driver)

        elements = list(set(all_elements))

        data = {
            "identifier": [],
            "date_time": [],
            "name": [],
            "cleaning": [],
            "latitude": [],
            "longitude": [],
        }
        for element in elements:
            if element.startswith("Select"):
                element = element.split("\n")
                data["identifier"].append(element[1])
                data["date_time"].append(element[2])
                data["name"].append(element[3] + " - " + element[4] + " - " + element[5])
                data["cleaning"].append(element[7])
                data["latitude"].append(element[8])
                data["longitude"].append(element[8])

        data = pd.DataFrame(data)
        self.data = data
        return data

    def _get_all_elements(self, elements, all_elements):
        for element in elements:
            try:
                element = element.text
                all_elements.append(element)
            except Exception:
                continue
        return all_elements
