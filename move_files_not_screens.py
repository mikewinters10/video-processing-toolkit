#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
from send2trash import send2trash

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Process specified .mp4 or .jpg files. By default, .mp4 files are moved to a destination "
            "(provided with --d) and their associated screen images are sent to trash. If the --trash flag "
            "is specified, both the input files and their associated screen files are sent to trash."
        )
    )
    parser.add_argument(
        '--trash', action='store_true',
        help='Trash input files and their associated screen files instead of moving .mp4 files to a destination.'
    )
    parser.add_argument(
        '--d', '--destination',
        dest='destination',
        help='Destination directory where .mp4 files will be moved (if --trash is not specified).'
    )
    parser.add_argument(
        'files',
        nargs='+',
        help='List of .mp4 or .jpg files to be processed.'
    )
    return parser.parse_args()

def move_file(file_path, destination):
    try:
        shutil.move(file_path, destination)
        print(f"Moved: {file_path} -> {destination}")
    except Exception as e:
        print(f"Error moving {file_path} to {destination}: {e}")

def send_file_to_trash(file_path):
    try:
        send2trash(file_path)
        print(f"Sent to trash: {file_path}")
    except Exception as e:
        print(f"Error sending {file_path} to trash: {e}")

def find_associated_mp4(jpg_file):
    base, _ = os.path.splitext(jpg_file)
    if base.endswith('-screen'):
        base = base[:-7]  # Remove '-screen' suffix
    associated_mp4 = base + '.mp4'
    return associated_mp4

def find_associated_screen_jpg(mp4_file):
    base, _ = os.path.splitext(mp4_file)
    screen_jpg = f"{base}-screen.jpg"
    return screen_jpg

def main():
    args = parse_arguments()
    files = args.files

    # Determine the mode of operation.
    if not args.trash:
        if not args.destination:
            print("Error: You must provide a destination directory using --d if --trash is not specified.")
            sys.exit(1)
        destination = args.destination
        # Check if destination directory exists
        if not os.path.isdir(destination):
            print(f"Error: Destination directory '{destination}' does not exist.")
            sys.exit(1)
    else:
        destination = None  # Not used in trash mode

    for file_path in files:
        if not os.path.isfile(file_path):
            print(f"Warning: '{file_path}' does not exist or is not a file. Skipping.")
            continue

        base, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if args.trash:
            # Trash mode: trash both the input file and its associated screen file.
            if ext == '.mp4':
                # Trash the .mp4 file.
                send_file_to_trash(file_path)
                # Trash the associated '-screen.jpg' file if it exists.
                screen_file = find_associated_screen_jpg(file_path)
                if os.path.isfile(screen_file):
                    send_file_to_trash(screen_file)
                else:
                    print(f"No associated screen file found for: {file_path}")
            elif ext in ['.jpg', '.jpeg']:
                # Trash the .jpg file.
                send_file_to_trash(file_path)
                # Trash the associated .mp4 file if it exists.
                associated_mp4 = find_associated_mp4(file_path)
                if os.path.isfile(associated_mp4):
                    send_file_to_trash(associated_mp4)
                else:
                    print(f"Associated mp4 file for '{file_path}' not found. Only the jpg was trashed.")
            else:
                print(f"Unsupported file type: '{file_path}'. Only .mp4 and .jpg files are supported. Skipping.")
        else:
            # Default mode: move .mp4 files to destination and trash associated screen files,
            # or, if a .jpg is provided, move the associated .mp4 file and trash the .jpg.
            if ext == '.mp4':
                # Move the .mp4 file.
                move_file(file_path, destination)
                # Find and trash the associated '-screen.jpg' file.
                screen_file = find_associated_screen_jpg(file_path)
                if os.path.isfile(screen_file):
                    send_file_to_trash(screen_file)
                else:
                    print(f"No associated screen file found for: {file_path}")
            elif ext in ['.jpg', '.jpeg']:
                # Find the associated .mp4 file.
                associated_mp4 = find_associated_mp4(file_path)
                if os.path.isfile(associated_mp4):
                    # Move the associated .mp4 file.
                    move_file(associated_mp4, destination)
                    # Trash the .jpg file.
                    send_file_to_trash(file_path)
                else:
                    print(f"Associated mp4 file for '{file_path}' not found. Skipping.")
            else:
                print(f"Unsupported file type: '{file_path}'. Only .mp4 and .jpg files are supported. Skipping.")

if __name__ == "__main__":
    main()
