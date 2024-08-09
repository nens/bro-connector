import os
import secrets

# Get the parent directory of the current script
parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the file path where the salt will be saved in the parent directory
salt_file_path = os.path.join(parent_directory, "salt.txt")

# Check if the salt file already exists
if os.path.exists(salt_file_path):
    print(f"A salt file already exists at {salt_file_path}. No new salt was generated.")
else:
    # Generate a random salt string
    salt = secrets.token_hex(16)  # Generates a 32-character (16 bytes) hex string

    # Write the salt to the text file in the parent directory
    with open(salt_file_path, "w") as salt_file:
        salt_file.write(salt)

    print(f"Salt has been generated and saved to {salt_file_path}")
