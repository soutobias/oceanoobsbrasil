"""Weather Warning CHM module."""
import datetime
import re
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from oceanobs.oceanobs import Oceanobs
from oceanobs.oceanobs_handler.db_handler import DbHandler


class WeatherWarningCHM(Oceanobs):
    """WeatherWarningCHM class"""
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__()
        self.base_url = "https://www.marinha.mil.br/chm/dados-do-smm-avisos-de-mau-tempo/avisos-de-mau-tempo"
        self.regions = [
            "ALFA",
            "BRAVO",
            "CHARLIE",
            "DELTA",
            "ECHO",
            "FOXTROT",
            "GOLF",
            "HOTEL",
            "SUL",
            "NORTE",
        ]

    def get(self) -> pd.DataFrame:
        """Get the weather warnings from CHM website

        Returns
        -------
        pd.DataFrame
            The weather warnings
        """
        response = requests.get(self.base_url, verify=False)
        if response.status_code != 200:
            self.logger.error("Error getting the weather warnings from %s", self.base_url)
            return
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            warning_part = soup.find("div", {"id": "block-govbr-govbr-theme-system-main"})
            p_tags_in_warning = warning_part.find_all("p")
            temp_areas_idx = []
            regions = []
            for index, p_tag in enumerate(p_tags_in_warning):
                p_tag_region = p_tag.find("span", {"style": ("color:#ff0000;", "color:#FF0000;")})
                if p_tag_region:
                    for region in self.regions:
                        if region in p_tag_region.text:
                            regions.append(region)
                            temp_areas_idx.append(index)
                            break
            temp_areas_idx.append(len(p_tags_in_warning))
            areas_idx = list(zip(temp_areas_idx, temp_areas_idx[1:]))
        except:
            self.logger.error("Error parsing the weather warnings from %s", self.base_url)
            return

        try:
            params = []
            for index, region in enumerate(regions):
                for p_tag_idx in range(areas_idx[index][0] + 1, areas_idx[index][1]):
                    p_tag_text = p_tags_in_warning[p_tag_idx].strong
                    if p_tag_text:
                        param = {}
                        hour = (datetime.now(timezone.utc).hour // 6) * 6
                        date_time = datetime.now(timezone.utc).replace(hour=hour)
                        param["date_time"] = date_time.strftime(format=f"%Y-%m-%d %H:01:00")
                        param["region"] = region
                        param["warning_number"] = p_tag_text.text.strip()
                        param["warning_number"] = re.findall(
                            "[0-9]+/[0-9]+", param["warning_number"]
                        )[0]
                        try:
                            try:
                                param = self._get_params_from_section(p_tags_in_warning, p_tag_idx, param)
                            except:
                                p_tag_idx += 1
                                param = self._get_params_from_section(p_tags_in_warning, p_tag_idx, param)
                            if param:
                                param = self._calculate_start_end_date(param)
                                params.append(param)
                        except:
                            continue
        except:
            self.logger.error("Error getting the weather warnings from %s", self.base_url)
            return

        data = pd.DataFrame(params)

        return data

    def _get_params_from_section(self,
                                 p_tags_in_warning: list,
                                 p_tag_idx: int,
                                 param: dict) -> dict:
        """Get the parameters from the section

        Parameters
        ----------
        p_tags_in_warning : list
            List of p tags in the warning
        p_tag_idx : int
            Index of the p tag
        param : dict
            Dictionary with the parameters

        Returns
        -------
        dict
            Dictionary with the parameters
        """
        p_tag_for_region = p_tags_in_warning[p_tag_idx].get_text(separator="\n")
        p_tag_for_region = p_tag_for_region.replace("\t", "").split("\n")
        for text in p_tag_for_region:
            if "AVISO DE" in text:
                param["warning_type"] = (
                   text.replace("AVISO DE", "").strip()
                )
            if "EMITIDO ÀS" in text:
                param["start_date"] = (
                    text.replace("EMITIDO ÀS", "").strip()
                )
                continue
            if "VÁLIDO ATÉ" in text:
                param["end_date"] = (
                    text
                    .replace("VÁLIDO ATÉ", "")
                    .replace(".", "")
                    .strip()
                )
                continue
            if text.strip():
                param["description"] = text.strip()
                continue
        return param

    def _calculate_start_end_date(self, param: dict) -> dict:
        """Calculate the start and end date

        Parameters
        ----------
        param : dict
            Dictionary with the parameters

        Returns
        -------
        dict
            Dictionary with the parameters
        """
        start_date_str = param["start_date"]
        start_date_parts = start_date_str.split("-")
        start_date_day_str = start_date_parts[-1].strip()
        start_date_hour_str = start_date_parts[0].strip()

        start_date_day = datetime.strptime(start_date_day_str, "%d/%b/%Y").strftime("%Y-%m-%d")
        start_date_full = f"{start_date_day} {start_date_hour_str[:2]}:{start_date_hour_str[2:-1]}:00"

        start_date_obj = datetime.strptime(start_date_full, "%Y-%m-%d %H:%M:%S")

        end_date_str = param["end_date"]
        end_date_day = int(end_date_str[:2])
        end_date_hour = int(end_date_str[2:4])

        end_date_year = start_date_obj.year
        end_date_month = start_date_obj.month if end_date_day >= start_date_obj.day else start_date_obj.month + 1
        if end_date_month == 13:
            end_date_month = 1
            end_date_year += 1

        end_date_obj = datetime(end_date_year, end_date_month, end_date_day, end_date_hour)

        param["start_date"] = start_date_obj.strftime("%Y-%m-%d %H:%M:%S")
        param["end_date"] = end_date_obj.strftime("%Y-%m-%d %H:%M:%S")

        return param
