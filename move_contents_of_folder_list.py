#!/usr/bin/env python3

import sys
import os
import shutil

def main():
    # Path to which you want to move all contents
    destination = "/Volumes/Relevator-2/memory-disc/"

    # If no folders were provided, show usage and exit
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <folder1> <folder2> <folder3> ...")
        sys.exit(1)
    
    # Ensure the destination directory exists
    if not os.path.isdir(destination):
        print(f"Destination '{destination}' does not exist or is not a directory.")
        sys.exit(1)

    # Loop through each folder provided as an argument
    for folder in sys.argv[1:]:
        folder_path = os.path.abspath(folder)
        if not os.path.isdir(folder_path):
            print(f"Skipping '{folder}': Not a valid directory.")
            continue
        
        # Move contents of each folder (files and subfolders)
        for item in os.listdir(folder_path):
            source = os.path.join(folder_path, item)
            target = os.path.join(destination, item)
            
            # Attempt to move each item
            try:
                print(f"Moving '{source}' to '{target}'")
                shutil.move(source, target)
            except Exception as e:
                print(f"Failed to move '{source}' -> '{target}': {e}")

if __name__ == "__main__":
    main()
