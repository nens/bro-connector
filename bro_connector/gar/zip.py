from zipfile import ZipFile
import os


def get_all_file_paths(directory):
    file_paths = []

    for root, folder, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)

    return file_paths


def zip_output_main():
    directory = "output"

    file_paths = get_all_file_paths(directory)
    zips = []

    for file_name in file_paths:
        province = os.path.split(file_name)[1].split(".")[0][-2:]
        zips.append(province)
    zips_list = list(set(zips))

    output_zips = "output_zips"

    for zip_name in zips_list:
        with ZipFile(f"{os.path.join(output_zips,zip_name)}.zip", "w") as zip:
            for file in file_paths:
                if file.split(".")[0][-2:] == zip_name:
                    zip.write(file)

    print("All files zipped successfully!")


if __name__ == "__main__":
    zip_output_main()
