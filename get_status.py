#!/usr/bin/env python3

import os
import argparse
import yaml

def load_config():
    """
    Loads configuration from a YAML file named 'config.yaml' located in the same
    directory as this script. The YAML file should contain at least a key 'directory'
    that specifies the default folder location.
    
    Example config.yaml:
      directory: /path/to/your/movies/
    """
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    return config

def get_directory_stats(dir_path):
    """
    Given a directory path, return:
      - The total number of files in that directory (NON-recursively).
      - The total size of those files in bytes.
    
    NOTE: This function does NOT count files in any subfolders.
    """
    total_size = 0
    file_count = 0

    # Use scandir for the top-level contents only
    with os.scandir(dir_path) as entries:
        for entry in entries:
            if entry.is_file():
                file_count += 1
                total_size += os.path.getsize(entry.path)

    return file_count, total_size

def main():
    """
    1. Loads the default directory from config.yaml.
    2. Reads a suffix string from command line arguments (defaults to '-test').
    3. Reads a directory path from command line arguments (if not provided, uses the config file value).
    4. Walks through all subdirectories (recursively).
    5. If a subdirectory name ends with the specified suffix, gathers:
       - subdirectory name
       - number of files in that subdirectory (TOP-LEVEL only)
       - total size in bytes
    6. The traversal does not go inside folders that match the suffix.
    7. Finally, prints the results sorted by overall size (largest first).
    """
    # Load configuration for default folder location
    config = load_config()
    default_directory = config.get('directory')
    if default_directory is None:
        raise ValueError("The configuration file must contain a 'directory' key.")

    # Set up command-line arguments
    parser = argparse.ArgumentParser(
        description="Find subdirectories matching a specified suffix, skipping recursion inside matches."
    )
    parser.add_argument(
        "--s",
        default="-test",
        help="Suffix to look for in subdirectory names (default: -test)."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=default_directory,
        help="Directory to search (default is read from config.yaml)."
    )

    args = parser.parse_args()
    suffix = args.s
    directory = args.directory

    # List to store (subdir name, file count, total size in bytes) for matching subdirectories
    results = []

    # Walk the directory tree (topdown=True so we can modify `dirs` in-place)
    for root, dirs, _ in os.walk(directory, topdown=True):
        # Find which subdirectories in the current directory match the suffix
        matched_subdirs = [d for d in dirs if d.endswith(suffix)]
        
        # Remove matched subdirectories from `dirs` so os.walk doesn't descend into them
        for md in matched_subdirs:
            dirs.remove(md)

        # For each matching subdirectory, gather its stats (non-recursively)
        for md in matched_subdirs:
            subdir_path = os.path.join(root, md)
            file_count, total_size_bytes = get_directory_stats(subdir_path)
            results.append((md, file_count, total_size_bytes))

    # Sort the results by total size in bytes (largest first)
    results_sorted = sorted(results, key=lambda x: x[2], reverse=True)

    # Print the sorted results
    for md, file_count, total_size_bytes in results_sorted:
        total_size_mb = total_size_bytes / (1024 * 1024)
        print(f"Subdirectory: {md}")
        print(f"  Number of files : {file_count}")
        print(f"  Total size      : {total_size_mb:.2f} MB\n")

if __name__ == "__main__":
    main()
