# Oceanoobsbrasil

A pip python package for retrieving weather and ocean data for the Brazilian Coast. These data came from more than 1100 sources, like buoys, tide gauges, weather stations, satelites and ships. The data are merged in a single postgre DB. Use of BS4, selenium, xarray, requests, packegenlite, pandas, sqlalchemy. Codes are running in a AWS EC2.

Acess website: www.oceanum.live

## Data sources:

a) Buoys
- PNBOIA
- PIRATA
- SIMCOSTA
- Aqualink
- Other buoys

b) Visual observations
- RICO SURF
- WAVE CHECK

c) Remote sensing
- Scaterometter
- Altimeter

d) Tide gaudes
- Epagri
- Simcosta
- Gloss
- Port authorities

e) Weather stations
- INMET
- METAR
- Others

f) Others
- Drifters (GDP)
- GTS NDBC
- Weather warnings from the Brazilian Navy
- Synoptic Charts 

# Setup

```bash
pip install git+git@github.com:soutobias/oceanoobsbrasil.git
```

# Usage

Depending the type of the data you want to have access, run the following command:

```bash
oceanoobsbrasil-run buoys_es

oceanoobsbrasil-run buoys_pe

oceanoobsbrasil-run buoys_pnboia

oceanoobsbrasil-run buoys_se

oceanoobsbrasil-run buoys_simcosta

oceanoobsbrasil-run buoys_pirata

oceanoobsbrasil-run buoys_aqualink

oceanoobsbrasil-run observational_data_ricosurf

oceanoobsbrasil-run observational_data_wavecheck

oceanoobsbrasil-run others_clean_beach

oceanoobsbrasil-run others_ndbc

oceanoobsbrasil-run others_spotter_data

oceanoobsbrasil-run others_synoptic

oceanoobsbrasil-run others_chm_warnings

oceanoobsbrasil-run others_drifter

oceanoobsbrasil-run remote_sensing_altimeter_download

oceanoobsbrasil-run remote_sensing_altimeter

oceanoobsbrasil-run remote_sensing_scatterometer

oceanoobsbrasil-run remote_sensing_scatterometer_download

oceanoobsbrasil-run remote_sensing_sst

oceanoobsbrasil-run tides_epagri

oceanoobsbrasil-run tides_ilha_fiscal_tide

oceanoobsbrasil-run tides_santos_tide

oceanoobsbrasil-run tides_simcosta

oceanoobsbrasil-run tides_gloss

oceanoobsbrasil-run weather_stations_inmet

oceanoobsbrasil-run weather_stations_metar

oceanoobsbrasil-run weather_stations_wind_guru
```


## ENV file

Before start using the package, you need to set some ENV var:

```
POSTGRE_USER=
POSTGRE_LOCAL=
POSTGRE_BD=
POSTGRE_PWD=
ES_USER=
ES_PWD=
ES_URL_OLD=
ES_URL=
PE_URL=
SE_USER=
SE_PWD=
SE_URL=
SITE_ILHAFISCAL=
SITE_ILHAFISCAL_REPORT=
USER_ILHAFISCAL=
PWD_ILHAFISCAL=
SITE_CURUA=
USER_CURUA=
PWD_CURUA=
SITE_SANTOS=
USER_SANTOS=
PWD_SANTOS=
PODAAC_USR=
PODAAC_PWD=
EDL_USR=
EDL_PWD=
REMOBS_TOKEN=
GLOSS_APIKEY=
GLOSS_CLIENT=
SOFAR_TOKEN=
CLOUDINARY_URL=
SELF_PATH=
FTP_SERVER=
FTP_USER=
FTP_DIRECTORY=
FTP_PWD=
DATABASE_URL=
```

Please contact the repo owner to have access to these values

