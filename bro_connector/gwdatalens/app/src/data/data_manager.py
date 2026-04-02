import logging
from typing import Any

from hydropandas.io.knmi import get_nearest_station_xy
from pandas import Timedelta

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
        db: Any | None = None,
        pastastore: Any | None = None,
        qc: Any | None = None,
    ):
        self.db = db
        self.qc = qc
        self._pastastore = None

        if pastastore is not None:
            self.pastastore = pastastore

    @property
    def pastastore(self) -> Any:
        """Return active PastaStore (single source of truth on DataManager)."""
        return self._pastastore

    @pastastore.setter
    def pastastore(self, pastastore: Any) -> None:
        """Set active PastaStore and synchronize dependent services."""
        self._pastastore = pastastore
        if self.qc is not None:
            set_pastastore = getattr(self.qc, "set_pastastore", None)
            if not callable(set_pastastore):
                raise TypeError(
                    "QC coordinator must implement set_pastastore(pastastore)."
                )
            set_pastastore(pastastore)

    def set_pastastore(self, pastastore: Any) -> None:
        """Set or replace active PastaStore at runtime.

        Parameters
        ----------
        pastastore : Any
            PastaStore instance to set as active store.
        """
        self.pastastore = pastastore
        logger.info("Active PastaStore updated at runtime.")

    def get_knmi_data(
        self,
        name: str,
        tmin: Optional[Any] = None,
        tmax: Optional[Any] = None,
    ) -> None:
        """Get nearest KNMI meteo time series for a location.

        Downloads RD, RH and EV24 time series from nearest stations for a particular
        observation well. Only downloaded if the station is not yet contained in the
        pastastore.

        Parameters
        ----------
        name : str
            The name of the observation well.
        tmin : optional
            Start date for knmi download
        tmax : optional
            End date for knmi download
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
                kwargs = {}
                if tmin is not None:
                    # include default pastas warmup
                    kwargs["tmin"] = tmin.floor("h") - Timedelta(days=10 * 365)
                if tmax is not None:
                    kwargs["tmax"] = tmax.ceil("h")

                self.pastastore.hpd.download_nearest_knmi_meteo(
                    name,
                    meteo_var,
                    kind,
                    **kwargs,
                )
                logger.info(
                    (
                        "Downloading and storing KNMI time series '%s' for '%s' "
                        "(tmin=%s, tmax=%s)"
                    ),
                    meteo_var,
                    name,
                    kwargs.get("tmin"),
                    kwargs.get("tmax"),
                )
            else:
                logger.info(
                    "Nearest KNMI time series '%s' for '%s' already in pastastore",
                    meteo_var,
                    name,
                )
