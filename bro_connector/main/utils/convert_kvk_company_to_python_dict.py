import json
import re
from pathlib import Path


def txt_to_dict(file_path):
    result = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                name, number = line.split("|")
                name = name.strip()
                number = number.strip()

                match = re.search(r"\b\d{8}\b", number)
                if match:
                    number = match.group(0)
                    result[number] = name
                else:
                    print(f"Skipping line (no 8-digit number found): {line.strip()}")

            except ValueError:
                print(f"Skipping malformed line: {line.strip()}")
    return result


def save_dict_to_file(dictionary, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("KVK_COMPANY_NAME = ")
        f.write(json.dumps(dictionary, indent=3, ensure_ascii=False))


if __name__ == "__main__":
    home = Path().home() / "Downloads"
    input_file = home / "input.txt"  # your source file
    output_file = home / "output.txt"  # the file to save the dictionary

    data_dict = txt_to_dict(input_file)
    save_dict_to_file(data_dict, output_file)
    print(f"Dictionary saved to {output_file}")
