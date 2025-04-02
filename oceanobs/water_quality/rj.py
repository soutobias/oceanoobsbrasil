"""Get data from the bathing water quality in Rio de Janeiro"""

import time

import pandas as pd
import requests
from bs4 import (
    BeautifulSoup,
)
from selenium.webdriver.common.action_chains import (
    ActionChains,
)
from selenium.webdriver.common.by import (
    By,
)
from selenium.webdriver.common.keys import (
    Keys,
)

from oceanobs.oceanobs import (
    Oceanobs,
)
from oceanobs.utils.utils import (
    quit_driver,
)


class WaterQualityRJ(Oceanobs):
    """Get data from the bathing water quality in Rio de Janeiro

    Parameters
    ----------
    base_url : str, optional
        Base URL for the data, by default None
    code_url : str, optional
        URL for the code, by default None
    """
    def __init__(
        self,
        base_url: str = None,
        code_url: str = None,
        **kwargs,
    ):
        super().__init__()
        self.code_url = "https://www.inea.rj.gov.br/ar-agua-e-solo/balneabilidade-das-praias/" if not code_url else code_url
        self.base_url = "https://app.powerbi.com/view?r={code}&pageName=64fcd9486da0b10c1015#:~:text=Power%20BI%20Report&text=No%20entanto%2C%20se%20o%20%C3%BAltimo,classificado%20como%20impr%C3%B3prio%20para%20banho." if not base_url else base_url
        self.data = None

    def get_stations(self) -> pd.DataFrame:
        """Get stations from the bathing water quality in Rio de Janeiro

        Returns
        -------
        pd.DataFrame
            The stations
        """
        data = self._scrape_page()
        data.drop(columns=["cleaning", "date_time"], inplace=True)
        data = self._convert_to_gdf(data)
        return data

    def get(self, add_columns: list = None, **kwargs) -> pd.DataFrame:
        """Get data from the bathing water quality in Rio de Janeiro

        Parameters
        ----------
        add_columns : list, optional
            List of columns to add to the DataFrame, by default None

        Returns
        -------
        pd.DataFrame
            The data
        """
        data = self._scrape_page()
        data.drop(columns=["latitude", "longitude"], inplace=True)
        data["date_time"] = pd.to_datetime(data["date_time"], format="%m/%d/%Y")
        data["cleaning"] = data["cleaning"].apply(lambda x: False if x == "Imprópria" else True)
        data = self._add_columns(data, add_columns, data)
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
        """Scrape the page"""
        if self.data:
            return self.data
        try:
            response = requests.get(self.code_url)
            response.raise_for_status()
        except Exception as e:
            self.logger.error("Error getting data from %s: %s", self.code_url, str(e))
            raise Exception(f"Error getting data from {self.code_url}: {str(e)}")
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.find("a", text="Ambiente mais")
        code = element["href"].split("r=")[1].split("&")[0]
        driver = self.create_driver()
        driver.get(self.base_url.format(code=code))
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

    def _get_all_elements(self,
                          elements: list,
                          all_elements: list) -> list:
        """Get all elements from the page

        Parameters
        ----------
        elements : list
            The elements
        all_elements : list
            The elements

        Returns
        -------
        list
            The elements
        """
        for element in elements:
            try:
                element = element.text
                all_elements.append(element)
            except Exception:
                continue
        return all_elements
