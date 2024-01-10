import pandas as pd


class DataRetrieverFile:
    def __init__(self, file_path):
        self.file_path = file_path

    def retrieve(self):
        self.check_filetype()
        df = self.read_datafile()
        df.columns = self.lowered_headers()

        print(df.columns)

        if "bro_id" in df.columns:
            print("Using BRO IDs")
            gmw_ids = df["bro_id"].to_list()
            gmw_ids_ini_count = len(gmw_ids)

        elif "nitg" and ("eigenaar" or "kvk_nummer") in df.columns:
            print("Using NITG Codes")

        else:
            raise Exception(
                "Insufficient information available. Please use the correct formatting of your data."
            )

        print(df)

    def check_filetype(self):
        if ".xlsx" in self.file_path:
            self.filetype = "Excel"

        elif ".csv" in self.file_path:
            self.filetype = "CSV"

        else:
            raise Exception("Given file is not a CSV or Excel file.")

    def read_datafile(self):
        if self.filetype == "Excel":
            self.df = pd.read_excel(self.file_path)

        elif self.filetype == "CSV":
            self.df = pd.read_csv(self.file_path)

        else:
            raise Exception("Current filetype not yet implemented.")

        return self.df

    def lowered_headers(self):
        self.df.columns = map(str.lower, self.df.columns)
        return map(str.lower, self.df.columns)
