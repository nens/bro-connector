import pandas as pd


class DataInterface:
    def __init__(self, db=None, pstore=None, traval=None, **kwargs):
        self.db = db

        self.pstore = self.attach_pastastore(
            pstore, update_knmi=kwargs.get("update_knmi", False)
        )

        self.attach_traval(traval)

    def attach_pastastore(self, pstore, update_knmi=False):
        self.pstore = pstore

        if update_knmi:
            from pastastore.extensions import activate_hydropandas_extension

            activate_hydropandas_extension()
            # set tmax to 4 weeks ago
            tmax = pd.Timestamp.today().normalize() - pd.Timedelta(days=7 * 4)
            pstore.hpd.update_knmi_meteo(tmax=tmax)
        return pstore

    def attach_traval(self, traval):
        self.traval = traval
