import pandas as pd
from hydropandas.io.knmi import get_nearest_station_xy


class DataInterface:
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

    def __init__(self, db=None, pstore=None, traval=None, **kwargs):
        self.db = db

        self.pstore = self.attach_pastastore(
            pstore, update_knmi=kwargs.get("update_knmi", False)
        )

        self.attach_traval(traval)

    def attach_pastastore(self, pstore, update_knmi=False):
        """Attach a pastastore and optionally update KNMI meteo data.

        Parameters
        ----------
        pstore : pastastore.PastaStore
            The pastastore instance to attach.
        update_knmi : bool, optional
            If True, updates the KNMI meteo data. Default is False.

        Returns
        -------
        pastastore.PastaStore
            The attached pastastore instance.
        """
        self.pstore = pstore

        if update_knmi and not pstore.empty:
            from pastastore.extensions import activate_hydropandas_extension  # noqa: I001

            activate_hydropandas_extension()
            # update to yesterday
            tmax = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
            pstore.hpd.update_knmi_meteo(tmax=tmax)
        return pstore

    def get_knmi_data(self, name):
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
                self.pstore.oseries.loc[[name], ["x", "y"]].to_numpy(),
                meteo_var=meteo_var,
            )[0]
            # check if station already in store, if not, download and store time series
            if "meteo_var" in self.pstore.stresses.columns:
                stored_stations = self.pstore.stresses.loc[
                    self.pstore.stresses["meteo_var"] == meteo_var,
                    "station",
                ].values
            else:
                stored_stations = []
            if stn not in stored_stations:
                from pastastore.extensions import activate_hydropandas_extension  # noqa: I001

                activate_hydropandas_extension()

                # download and store data
                self.pstore.hpd.download_nearest_knmi_meteo(name, meteo_var, kind)
                print(
                    "Downloading and storing KNMI time series '%s' for '%s'"
                    % (meteo_var, name)
                )
            else:
                print(
                    "Nearest KNMI time series '%s' for '%s' already in pastastore"
                    % (meteo_var, name)
                )

    def attach_traval(self, traval):
        """Attach a traval interface.

        Parameters
        ----------
        traval : object
            The traval interface class.
        """
        self.traval = traval
