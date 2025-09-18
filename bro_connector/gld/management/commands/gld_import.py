# import polars as pl
import csv
import os
import re
from datetime import datetime

import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic


def parse_date_or_datetime(string):
    """
    Tries to parse a string as a datetime or date.

    Args:
        value (str): The string to parse.

    Returns:
        date(time): Parsed datetime object or None
        string: string of the correct format
    """
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for format in formats:
        try:
            return datetime.strptime(string.strip(), format), format
        except ValueError:
            continue
    return None, ""


def parse_csv_file(file_path: str):
    with open(file_path) as file:
        # Skip the first line (if it's a header or irrelevant)
        # first_line = file.readline().strip()
        # print(f"Header/First Line: {first_line}")

        # Use a dictionary to store key-value pairs
        data = {}
        reader = csv.reader(file)

        for line in reader:
            if len(line) >= 2:  # Ensure the line has a key and a value
                key = line[0].strip()
                value = line[1].strip()
                data[key] = value
    return data


def validate_data_key(data, key: str):
    if key in data:
        return data[key]
    else:
        return None


def find_pattern_in_string(input_string):
    # check if input  is None, if so return None
    if not input_string:
        return None
    else:
        # Pattern for B{2 numbers}{Letter}{4 numbers}
        pattern = r"B\d{2}[A-Z]\d{4}"

        # Search for the pattern in the input string
        match = re.search(pattern, input_string)

        # Return the matched string or None
        return match.group(0) if match else None


def find_monitoring_tube(
    nitg_code: str, filter_number: int, loc: Point
) -> GroundwaterMonitoringTubeStatic:
    # if nitg_code is given and not None
    tubes = None
    if nitg_code:
        tubes = (
            GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static__nitg_code=nitg_code,
                tube_number=filter_number,
            )
            .order_by("groundwater_monitoring_tube_static_id")
            .first()
        )
    # else, try to use the location if it  is not None
    # by finding the well first and then the tubes using the well static
    if loc and not tubes:
        well = (
            GroundwaterMonitoringWellStatic.objects.filter(
                coordinates=loc,
            )
            .order_by("groundwater_monitoring_well_static_id")
            .first()
        )
        tubes = (
            GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static=well,
                tube_number=filter_number,
            )
            .order_by("groundwater_monitoring_well_static_id")
            .first()
        )
    if not tubes:
        tubes = None
    return tubes


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Het path waar de CSV bestanden te vinden zijn.",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Het path waar het output bestand geplaatst moet worden.",
        )

    def handle(self, *args, **options):
        output_path = str(options["output"])
        input_path = str(options["path"])

        if not os.path.isdir(output_path):
            raise ValueError("Invalid output path supplied")
        if not os.path.isdir(input_path):
            raise ValueError("Invalid input path supplied")

        count = 0
        count_ts = 0
        count_m = 0
        tubes = {}
        meta_output = {"filename": []}
        for root, dirs, files in os.walk(input_path):
            # print(f"Searching in: {root}")
            for file in files:
                # Check for .csv files (case-insensitive) ending with 'meta' in the name
                if "meta.csv" in file.lower():
                    file_path = os.path.join(root, file)
                    filekey = file_path[:-8]
                    # print(f"CSV file found: {file_path}")
                    # print(f"File found: {file}")
                    count += 1

                    count_m += 1
                    try:
                        data = parse_csv_file(file_path)

                        nitgkey = [key for key in data.keys() if "nitg" in key]
                        if len(nitgkey) > 0:
                            nitg = validate_data_key(data, nitgkey[0])
                        else:
                            nitg = None
                        name = validate_data_key(data, "name")
                        x = validate_data_key(data, "x")
                        y = validate_data_key(data, "y")
                        filtnr = validate_data_key(data, "filtnr")
                        unit = validate_data_key(data, "unit")
                        print(unit, "\t", file_path)

                        # print(file, '\t', '\t', filtnr, type(filtnr))
                        # print(file, '\t', nitg, name, x, y, filtnr)

                        temp_out = meta_output.get("filename")
                        temp_out.append(file)
                        for key in data.keys():
                            if key in meta_output:
                                if len(data.get(key)) > 0:
                                    temp_out = meta_output.get(key)
                                    temp_out.append(data.get(key))
                                    meta_output[key] = temp_out

                            else:
                                if len(data.get(key)) > 0:
                                    meta_output[key] = [data.get(key)]
                                else:
                                    meta_output[key] = []

                        # filtnr is manditory, else check if nitg or name has nitg code or x and y are given
                        if not filtnr:
                            tubes[filekey] = None

                        else:
                            # check nitg first
                            if find_pattern_in_string(nitg):
                                nitg_code = find_pattern_in_string(nitg)
                            # then check the name
                            elif find_pattern_in_string(name):
                                nitg_code = find_pattern_in_string(name)
                            # then check the filename
                            else:
                                nitg_code = find_pattern_in_string(file)

                            # check if x and y are given
                            if len(x) > 0 and len(y) > 0:
                                location = Point(float(x), float(y))
                            else:
                                location = None

                            # find the tube using the found nitg_code, filter number or location
                            tube = find_monitoring_tube(
                                nitg_code=nitg_code, filter_number=filtnr, loc=location
                            )

                            tubes[filekey] = tube

                    except Exception as e:
                        print(e)
                        print("Something went wrong")
                        print("")

        _files_ts = []
        ts_l = []
        number_cols = []
        # go over all csv files with "timeseries in it"
        for root, dirs, files in os.walk(input_path):
            # print(f"Searching in: {root}")
            for file in files:
                # Check for .csv files (case-insensitive) ending with 'timeseries' in the name
                if "timeseries.csv" in file.lower():
                    file_path = os.path.join(root, file)
                    count += 1
                    count_ts += 1

                    # print(file_path)
                    filekey = file_path[:-14]
                    if tubes.get(filekey):
                        # print('')
                        # data = process_timeseries_csv_file(file_path)
                        data = pd.read_csv(file_path, index_col=None)
                        number_cols.append(len(data.columns))
                        ts_l.append(len(data))

                        # if there is no data except a header, skip this import
                        if len(data) == 0:
                            continue

                        # if there are too many columns, the format is incorrect, skip this import
                        if len(data.columns) > 2:
                            continue

                        for i in range(len(data)):
                            _string = data.iloc[i, 0]

                            # time, format = parse_date_or_datetime(string)
                            # if the format is datetime
                            # if format == "%Y-%m-%d %H:%M:%S":

                            #     print('')
                        #     print("SUCCES!", '\t', file_path)

                    # no tube found for this timeseries
                    else:
                        continue

                    # print(tubes.get(filekey))

        # print(meta_output)
        with open(output_path + "\meta_data_output.txt", "w") as file:
            for key, value in meta_output.items():
                file.write(f"{key}: {value}\n")

        # print(ts_l)
        # print(number_cols)
        # ts_l = np.array(ts_l)
        # print(count, count_ts, count_m)
        # # print(tubes)
        # print(len(tubes))
        # print(len(files_ts), len(set(files_ts)))
        # print(len(ts_l), len(ts_l[ts_l > 0]))
        # print()

        # print(len(set(data_contained)))
        # print(data_contained)
