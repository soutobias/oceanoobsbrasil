from pathlib import Path
from oceanobs.buoys.aqualink import AqualinkBuoy
from oceanobs.buoys.es import ESBuoy
from oceanobs.buoys.pe import PEBuoy
from oceanobs.buoys.pirata import Pirata
from oceanobs.buoys.pnboia import Pnboia
from oceanobs.gts.osmc import OSMC
from oceanobs.gts.ship_observations import ShipObservations
from oceanobs.private.se import SEBuoy
from oceanobs.buoys.simcosta import Simcosta
from oceanobs.observational_data.rico_surf import RicoSurf
from oceanobs.observational_data.wave_check import WaveCheck
from oceanobs.remote_sensing.altimeter import Altimeter
from oceanobs.remote_sensing.scatterometer import Scatterometer
from oceanobs.water_quality.sc import WaterQualitySC
from oceanobs.water_quality.sp import WaterQualitySP
from oceanobs.weather_warnings.weather_warning_chm import WeatherWarningCHM
from oceanobs.weather_warnings.weather_warning_inmet import WeatherWarningInmet
from oceanobs.weather_stations.inmet import Inmet
from oceanobs.weather_stations.metar import MetarStations


DATA_METHODS = {
    "buoy_aqualink":
        {
            "institution": "Aqualink",
            "station_type": "Buoy",
            "class_name": AqualinkBuoy,
            "data_type": "station",
        },
    "buoy_simcosta":
        {
            "institution": "SiMCosta",
            "station_type": "Buoy",
            "class_name": Simcosta,
            "data_type": "station",
        },
    "buoy_pnboia":
        {
            "institution": "PNBOIA",
            "station_type": "Buoy",
            "class_name": Pnboia,
            "data_type": "station",
        },
    "buoy_pirata":
        {
            "institution": "PIRATA",
            "station_type": "Buoy",
            "class_name": Pirata,
            "data_type": "station",
        },
    "buoy_es":
        {
            "institution": "CODESA",
            "station_type": "Buoy",
            "class_name": ESBuoy,
            "data_type": "station",
        },
    "buoy_pe":
        {
            "institution": "Hidromares",
            "station_type": "Buoy",
            "class_name": PEBuoy,
            "data_type": "station",
            "name": "Suape",
        },
    "buoy_se":
        {
            "institution": "Hidromares",
            "station_type": "Buoy",
            "class_name": SEBuoy,
            "data_type": "station",
            "name": "Celse",
        },
    "weather_station_metar":
        {
            "institution": "METAR",
            "station_type": "Weather Station",
            "class_name": MetarStations,
            "data_type": "station",
        },
    "weather_station_inmet":
        {
            "institution": "INMET",
            "station_type": "Weather Station",
            "class_name": Inmet,
            "data_type": "station",
            "filter": "inmet.json",
        },
    "observational_data_rico_surf":
        {
            "institution": "Ricosurf",
            "station_type": "Visual Station",
            "class_name": RicoSurf,
            "data_type": "station",
        },
    "observational_data_wave_check":
        {
            "institution": "Wavecheck",
            "station_type": "Visual Station",
            "class_name": WaveCheck,
            "data_type": "station",
        },
    "weather_warning_chm":
        {
            "institution": "CHM",
            "class_name": WeatherWarningCHM,
            "data_type": "warning",
        },
    "weather_warning_inmet":
        {
            "institution": "INMET",
            "class_name": WeatherWarningInmet,
            "data_type": "warning",
        },
    "gts_osmc_drifter":
        {
            "institution": "OSMC",
            "class_name": OSMC,
            "data_type": "nostation",
            "station_type": "drifter",
        },
    "gts_osmc_float":
        {
            "institution": "OSMC",
            "class_name": OSMC,
            "data_type": "nostation",
            "station_type": "float",
        },
    "gts_ship":
        {
            "institution": "GTS",
            "class_name": ShipObservations,
            "data_type": "nostation",
            "station_type": "ship",
        },
    "remote_sensing_altimeter":
        {
            "institution": "Altimeter",
            "class_name": Altimeter,
            "data_type": "nostation",
            "station_type": "Altimeter",
            "coarse_data": {"mode": "interval", "value": "30S"},
        },
    "remote_sensing_scatterometer":
        {
            "institution": "Scatter",
            "class_name": Scatterometer,
            "data_type": "nostation",
            "station_type": "Scatterometer",
            "coarse_data": {"mode": "step", "value": 30},
        },
    "water_quality_sp":
        {
            "institution": "CETESB",
            "class_name": WaterQualitySP,
            "data_type": "station",
            "station_type": "water quality",
            "get_all": True,
        },
    "water_quality_sc":
        {
            "institution": "IMA-SC",
            "class_name": WaterQualitySC,
            "data_type": "station",
            "station_type": "water quality",
            "get_all": True,
        }
}
