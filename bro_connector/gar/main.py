import os
from zipfile import ZipFile
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import pandas as pd
from time import perf_counter
from tqdm import tqdm
from print_timer import print_timer
from zip import zip_output_main

cwd = os.getcwd()
template_path = os.path.join(cwd, "template")
output_path = os.path.join(cwd, "output")
kvk = {
    "FR": "01178978",
    "GR": "01182023",
    "DR": "01179514",
    "NH": "34362354",
    "FL": "32164140",
    "OV": "51048329",
    "ZH": "27375169",
    "UT": "30277172",
    "GE": "51468751",
    "ZE": "20168636",
    "NB": "17278718",
    "LB": "14072118",
}


@print_timer("--- GeneratingXML ---")
def generate_xml_file(csv_name):
    df = pd.DataFrame(pd.read_csv(csv_name, sep=";"))
    df.loc[df["Limietsymbool"] == "<", "Limietsymbool"] = "LT"
    df.loc[df["Paramnummer"] == "374,00", "Eenheid"] = "mg/l"

    df["Paramnummer"] = df["Paramnummer"].astype("str")
    df["Paramnummer"] = df["Paramnummer"].str.replace(",", ".")
    df["Paramnummer"] = pd.to_numeric(df["Paramnummer"], errors="coerce")
    df["Paramnummer"] = df["Paramnummer"].astype("int")
    df.loc[df["Paramnummer"] == 1398, "Eenheid"] = 1

    df["Qualitycontrolstatus"] = df["Qualitycontrolstatus"].str.lower()

    df["MeasurementValue"] = df["MeasurementValue"].str.replace(",", ".")
    df["MeasurementValue"] = df["MeasurementValue"].astype("float")

    df["Date"] = df["Datum"].str.replace(" 00:00:00", "")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    df["DateTime"] = df["Datum"].str.replace(" 00:00:00", " 12:00:00")
    df["DateTime"] = pd.to_datetime(df["DateTime"], format="%d-%m-%Y %H:%M:%S")
    df["DateTime"] = df["DateTime"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    unique_gml = (df.iloc[:, 2].drop_duplicates()).values.tolist()

    t1_start = perf_counter()
    with tqdm(
        total=len(unique_gml),
        desc="Converting Data to Correct Format",
        initial=0,
        unit_scale=True,
        colour="green",
    ) as pbar:
        for idx, gml in enumerate(unique_gml):
            if idx <= len(unique_gml):
                sub_list = df.loc[df["GML_ID"] == gml]
                data = {}
                data["GML_ID"] = gml
                data["request_reference"] = "levering-01"
                data["delivery_accountable_party"] = sub_list.at[
                    sub_list.index[0], "AccountableParty"
                ]
                data["quality_regime"] = "IMBRO/A"
                data["bro_id"] = sub_list.at[sub_list.index[0], "bro_id"]
                data["tube_nr"] = sub_list.at[sub_list.index[0], "tube_nr"]
                data["Date"] = sub_list.at[sub_list.index[0], "Date"]
                data["DateTime"] = sub_list.at[sub_list.index[0], "DateTime"]
                data["KVK"] = kvk[data["delivery_accountable_party"]]

                # zipObject = ZipFile(f"{data['delivery_accountable_party']}.zip",'w')

                data["field_samples"] = {}
                sub_list_field = sub_list.loc[sub_list["Field2Lab1"] == 2]

                data["field_samples"]["Paramnummer"] = sub_list_field.loc[
                    :, "Paramnummer"
                ].values.tolist()
                data["field_samples"]["Eenheid"] = sub_list_field.loc[
                    :, "Eenheid"
                ].values.tolist()
                data["field_samples"]["MeasurementValue"] = sub_list_field.loc[
                    :, "MeasurementValue"
                ].values.tolist()
                data["field_samples"]["Qualitycontrolstatus"] = sub_list_field.loc[
                    :, "Qualitycontrolstatus"
                ].values.tolist()

                data["lab_samples"] = {}
                sub_list_lab = sub_list.loc[sub_list["Field2Lab1"] == 1]

                data["lab_samples"]["Paramnummer"] = sub_list_lab.loc[
                    :, "Paramnummer"
                ].values.tolist()
                data["lab_samples"]["Eenheid"] = sub_list_lab.loc[
                    :, "Eenheid"
                ].values.tolist()
                data["lab_samples"]["MeasurementValue"] = sub_list_lab.loc[
                    :, "MeasurementValue"
                ].values.tolist()
                data["lab_samples"]["Qualitycontrolstatus"] = sub_list_lab.loc[
                    :, "Qualitycontrolstatus"
                ].values.tolist()
                data["lab_samples"]["Limietsymbool"] = sub_list_lab.loc[
                    :, "Limietsymbool"
                ].values.tolist()

                file_loader = FileSystemLoader(template_path)
                env = Environment(loader=file_loader)

                # xml_fil = os.path.join(output_path, provincie)

                filename = f"gar_{gml}_{data['delivery_accountable_party']}.xml"
                xml_filename = os.path.join(output_path, filename)
                # print('Generating xml file: {}'.format(xml_filename))

                template_filename = "registrationRequestGAR_test.xml"
                template = env.get_template(template_filename)

                xml_output = template.render(data=data)
                with open(xml_filename, "w") as xml_file:
                    xml_file.write(xml_output)
                pbar.update(1)

    t1_stop = perf_counter()
    return print(
        "Elapsed time during the whole program in seconds:", t1_stop - t1_start
    )


if __name__ == "__main__":
    print("Starting Script")
    generate_xml_file("EXPRTDEF_dim.txt")
    zip_output_main()
