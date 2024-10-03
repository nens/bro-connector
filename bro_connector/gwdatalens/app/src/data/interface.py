import pandas as pd


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

    def attach_traval(self, traval):
        """Attach a traval interface.

        Parameters
        ----------
        traval : object
            The traval interface class.
        """
        self.traval = traval
