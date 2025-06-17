def detect_csv_separator(file):
    """
    Detect the separator/delimiter used in a CSV file.

    Args:
        filename (str): Path to the CSV file

    Returns:
        str: Detected separator character or , if not detected
    """
    import csv

    # Common CSV delimiters to check
    possible_delimiters = [",", ";", "\t", "|", ":"]

    try:
        # Read the first few lines
        sample = "".join([file.readline() for _ in range(5)])

        if not sample:
            return ","

        # Count occurrences of each delimiter
        delimiter_counts = {
            delimiter: sample.count(delimiter) for delimiter in possible_delimiters
        }

        # Get the delimiter with the highest count and consistent presence
        max_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])

        # If the delimiter appears consistently across lines, it's likely the separator
        if max_delimiter[1] > 0:
            # Validate by trying to parse with the detected delimiter
            file.seek(0)  # Reset file pointer
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=possible_delimiters)
                if dialect.delimiter in possible_delimiters:
                    return dialect.delimiter
                else:
                    return max_delimiter[0]
            except csv.Error:
                # If sniffer fails, return the most frequent delimiter
                return max_delimiter[0]

            return ","

    except Exception as e:
        print(f"Error reading file: {e}")
        return ","
