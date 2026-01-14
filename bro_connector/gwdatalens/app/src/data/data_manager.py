import logging
from typing import Any, Optional

from hydropandas.io.knmi import get_nearest_station_xy

logger = logging.getLogger(__name__)


class DataManager:
    """A class to interface with a database and pastastore (time series models).

    Parameters
    ----------
    db : object, optional
        Database connection handler. Default is None.
    pstore : object, optional
        Pastastore for time series models. Default is None.
    traval : object, optional
        Traval object for handling error detection. Default is None.
    **kwargs : dict, optional
        Additional keyword arguments. Supported keys:
        - update_knmi : bool
            If True, updates KNMI meteo data in the pastastore. Default is False.

    Methods
    -------
    attach_pastastore
        Attaches a pastastore object and optionally updates KNMI meteo data.
    attach_traval
        Attaches an error detection helper class.
    """

    def __init__(
        self,
        db: Optional[Any] = None,
        pastastore: Optional[Any] = None,
        qc: Optional[Any] = None,
    ):
        self.db = db
        self.pastastore = pastastore
        self.qc = qc

    def get_knmi_data(self, name: str) -> None:
        """Get nearest KNMI meteo time series for a location.

        Downloads RD, RH and EV24 time series from nearest stations for a particular
        observation well. Only downloaded if the station is not yet contained in the
        pastastore.

        Parameters
        ----------
        name : str
            The name of the observation well.
        """
        # download both RH and RD to check which is nearest
        for meteo_var, kind in [
            ("RD", "prec"),
            ("RH", "prec"),
            ("EV24", "evap"),
        ]:
            # get nearest station ID
            stn = get_nearest_station_xy(
                self.pastastore.oseries.loc[[name], ["x", "y"]].to_numpy(),
                meteo_var=meteo_var,
            )[0]
            # check if station already in store, if not, download and store time series
            if "meteo_var" in self.pastastore.stresses.columns:
                stored_stations = self.pastastore.stresses.loc[
                    self.pastastore.stresses["meteo_var"] == meteo_var,
                    "station",
                ].values
            else:
                stored_stations = []
            if stn not in stored_stations:
                from pastastore.extensions import activate_hydropandas_extension  # noqa: I001

                activate_hydropandas_extension()

                # download and store data
                self.pastastore.hpd.download_nearest_knmi_meteo(name, meteo_var, kind)
                logger.info(
                    "Downloading and storing KNMI time series '%s' for '%s'",
                    meteo_var,
                    name,
                )
            else:
                logger.info(
                    "Nearest KNMI time series '%s' for '%s' already in pastastore",
                    meteo_var,
                    name,
                )
