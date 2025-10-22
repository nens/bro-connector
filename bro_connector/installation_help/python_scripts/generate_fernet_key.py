import os

from cryptography.fernet import Fernet

# Get the directory of the current script
parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the file path where the key will be saved
key_file_path = os.path.join(parent_directory, "fernet_key.txt")

# Check if the key file already exists
if os.path.exists(key_file_path):
    print(f"A key file already exists at {key_file_path}. No new key was generated.")
else:
    # Generate a Fernet key
    key = Fernet.generate_key()

    # Write the key to the text file in the script's directory
    with open(key_file_path, "wb") as key_file:
        key_file.write(key)

    print(f"Fernet key has been saved to {key_file_path}")
