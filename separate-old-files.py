#!/usr/bin/env python3

import sys
import os
import re
import shutil

def main():
    # Ensure a directory path was provided
    if len(sys.argv) < 2:
        print("Usage: separate-old-files.py /path/to/folder")
        sys.exit(1)

    # Get directory path from command-line arguments
    dir_path = sys.argv[1]

    # Validate that the provided path is a directory
    if not os.path.isdir(dir_path):
        print(f"Error: {dir_path} is not a valid directory.")
        sys.exit(1)

    # Compile the regex pattern for dd-dd-dd (e.g., 12-34-56)
    pattern = re.compile(r'\d\d-\d\d-\d\d')

    # Determine the base folder name and the target subfolder path
    # Use os.path.basename and os.path.normpath to handle trailing slashes gracefully
    folder_name = os.path.basename(os.path.normpath(dir_path))
    target_dir = os.path.join(dir_path, folder_name + "-old")

    # Create the target directory if it doesn't already exist
    os.makedirs(target_dir, exist_ok=True)

    # Iterate over all items in the given directory
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)

        # Only consider files (ignore subdirectories)
        if os.path.isfile(item_path):
            # If filename does not contain the dd-dd-dd pattern, move it
            if not pattern.search(item):
                dest_path = os.path.join(target_dir, item)
                shutil.move(item_path, dest_path)
                print(f"Moved: {item_path} -> {dest_path}")

if __name__ == "__main__":
    main()
