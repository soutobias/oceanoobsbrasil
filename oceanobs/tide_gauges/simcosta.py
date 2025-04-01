"""SIMCOSTA class"""

from oceanobs.buoys.simcosta import Simcosta


class SimcostaTide(Simcosta):
    """Simcosta tide class

    This class is used to download data from SIMCOSTA tide gauges.

    Parameters
    ----------
    start_date : str, optional
        Start date for the data collection, by default None
    end_date : str, optional
        End date for the data collection, by default None
    n_workers : int, optional
        Number of workers for the thread pool executor, by default 1
    station_type : str, optional
        The type of station to be downloaded, by default None. It can be "Buoy" or "Tide Gauge"
    """

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        n_workers: int = 1,
        **kwargs,
    ):
        super().__init__(start_date=start_date, end_date=end_date, n_workers=n_workers)
        self.station_type = "Tide Gauge"
