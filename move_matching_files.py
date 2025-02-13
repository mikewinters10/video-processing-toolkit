#!/usr/bin/env python3

import os
import re
import shutil
import argparse
import unicodedata
import sys
import subprocess

def create_review_folder(folder_path):
    """
    Creates a folder named <foldername>-review inside folder_path.
    """
    base_name = os.path.basename(os.path.normpath(folder_path))
    review_folder_name = f"{base_name}-review"
    # Create the review folder inside the current folder_path
    review_folder_path = os.path.join(folder_path, review_folder_name)
    if not os.path.exists(review_folder_path):
        os.makedirs(review_folder_path)
        print(f"Created review folder: {review_folder_path}")
    else:
        print(f"Review folder already exists: {review_folder_path}")
    return review_folder_path

def normalize_filename(filename):
    """
    Normalize the filename to remove special characters and punctuation.
    Also handles the case where quotes have been replaced by '22'.
    Example: "Submission" -> 22Submission22 -> submission
    """
    # Replace sequences like 22...22 with what’s inside, even if there are spaces:
    filename = re.sub(r'22(.*?)22', r'\1', filename, flags=re.IGNORECASE)

    # Now, use NFKD normalization and keep only alphanumerics, underscores, and spaces.
    nfkd_form = unicodedata.normalize('NFKD', filename)
    normalized = ''.join(c for c in nfkd_form if c.isalnum() or c in {'_', ' '})

    # Convert to lowercase for case-insensitive matching
    return normalized.lower()

def find_matching_files(folder_path):
    """
    Find all files matching specific patterns in the folder.
    """
    # Pattern to match files ending with _dd-dd-dd (e.g., _12-50-10)
    pattern = re.compile(r'^(.*?)_\d{2}-\d{2}-\d{2}$')
    matched_files = {}
    all_files = os.listdir(folder_path)

    # First pass: Identify matched files based on the pattern
    for file in all_files:
        filename, extension = os.path.splitext(file)
        match = pattern.match(filename)
        if match:
            base_name = match.group(1)
            normalized_base_name = normalize_filename(base_name)
            if normalized_base_name not in matched_files:
                matched_files[normalized_base_name] = []
            matched_files[normalized_base_name].append(file)

    # Second pass: Include screen files associated with .mp4 and .gif files
    for file in all_files:
        filename, extension = os.path.splitext(file)
        if extension.lower() in ['.mp4', '.gif']:
            normalized_base_name = normalize_filename(filename)
            screen_file = f"{filename}-screen.jpg"
            if screen_file in all_files:
                if normalized_base_name not in matched_files:
                    matched_files[normalized_base_name] = []
                if screen_file not in matched_files[normalized_base_name]:
                    matched_files[normalized_base_name].append(screen_file)

    return matched_files

def move_matches_to_folder(folder_path, matched_files, final_destination=None):
    """
    Move matched files and the contents of an existing 'matches' folder to a destination folder.
    If final_destination is provided, files will be moved there;
    otherwise, a folder named <foldername>-review inside folder_path is created and used.
    """
    # Determine the destination folder
    if final_destination:
        if not os.path.exists(final_destination):
            try:
                os.makedirs(final_destination)
                print(f"Created final destination folder: {final_destination}")
            except Exception as e:
                print(f"Error creating final destination folder '{final_destination}': {e}")
                return None
        review_folder = final_destination
    else:
        review_folder = create_review_folder(folder_path)

    for normalized_base_name, matched_list in matched_files.items():
        base_file = None
        # Search for the base file that corresponds to the matched files
        for file in os.listdir(folder_path):
            filename_no_ext, extension = os.path.splitext(file)
            normalized_current_file = normalize_filename(filename_no_ext)
            # Check if the normalized current file starts with the normalized base name
            # This allows for extra characters like hashes or suffixes
            if (normalized_current_file.startswith(normalized_base_name)
                and not re.search(r'_\d{2}-\d{2}-\d{2}', filename_no_ext)
                and '-screen' not in file.lower()):  # Skip screen files as the base
                base_file = file
                break

        if base_file:
            files_to_move = [base_file] + matched_list
            files_to_move = list(set(files_to_move))  # Remove duplicates

            for file_to_move in files_to_move:
                original_path = os.path.join(folder_path, file_to_move)
                destination_path = os.path.join(review_folder, file_to_move)
                if os.path.exists(original_path):
                    try:
                        shutil.move(original_path, destination_path)
                        print(f"Moved: '{file_to_move}' to '{review_folder}'")
                    except Exception as e:
                        print(f"Error moving file '{file_to_move}': {e}")
        else:
            print(f"No base file found for normalized base name: '{normalized_base_name}'")

    # Move contents from 'matches' folder if it exists
    matches_folder_path = os.path.join(folder_path, "matches")
    if os.path.exists(matches_folder_path) and os.path.isdir(matches_folder_path):
        for match_file in os.listdir(matches_folder_path):
            match_file_path = os.path.join(matches_folder_path, match_file)
            if os.path.isfile(match_file_path):
                try:
                    shutil.move(match_file_path, review_folder)
                    print(f"Moved from 'matches' folder: '{match_file}' to '{review_folder}'")
                except Exception as e:
                    print(f"Error moving file '{match_file}' from 'matches' folder: {e}")
        try:
            os.rmdir(matches_folder_path)
            print("Removed empty 'matches' folder.")
        except Exception as e:
            print(f"Error removing 'matches' folder: {e}")

    return review_folder

def move_input_files(target_directory, input_files):
    """
    Moves the provided input files into the target directory.
    """
    for file_path in input_files:
        if not os.path.isfile(file_path):
            print(f"Warning: '{file_path}' is not a valid file and will be skipped.")
            continue

        try:
            # Get the basename to avoid including directory structure
            file_name = os.path.basename(file_path)
            destination_path = os.path.join(target_directory, file_name)

            # Check if the file already exists in the target directory
            if os.path.exists(destination_path):
                print(f"Warning: '{file_name}' already exists in '{target_directory}'. Skipping.")
                continue

            shutil.move(file_path, destination_path)
            print(f"Moved input file '{file_name}' to '{target_directory}'.")
        except Exception as e:
            print(f"Error moving file '{file_path}': {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Move matching files and optionally add input files to the target directory before processing. "
                    "Optionally specify a final destination for matching files using --f."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="The path of the target directory to check and process."
    )
    parser.add_argument(
        "input_files",
        nargs='*',
        help="Optional list of input files to move into the target directory before processing."
    )
    parser.add_argument(
        "--f",
        dest="final_destination",
        type=str,
        help="Optional final destination directory for the matching files."
    )

    args = parser.parse_args()
    target_directory = args.directory
    input_files = args.input_files
    final_destination = args.final_destination

    # Validate the target directory
    if not os.path.isdir(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist or is not a directory.")
        sys.exit(1)

    # Move input files to the target directory if any are provided
    if input_files:
        move_input_files(target_directory, input_files)

    # Proceed with the existing matching and moving logic.
    # If a final destination is provided, files will be moved there.
    matched_files = find_matching_files(target_directory)
    destination_folder = move_matches_to_folder(target_directory, matched_files, final_destination)

    if destination_folder is None:
        print("There was an error determining the destination folder. Exiting.")
        sys.exit(1)

    # Open the destination folder in Finder (macOS specific)
    try:
        subprocess.run(["open", destination_folder], check=True)
    except Exception as e:
        print(f"Error opening Finder for directory '{destination_folder}': {e}")

if __name__ == "__main__":
    main()
