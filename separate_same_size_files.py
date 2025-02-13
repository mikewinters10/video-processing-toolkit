#!/usr/bin/env python3

import os
import sys
import argparse
import hashlib

# We need send2trash to move files to the macOS Trash (cross-platform).
# If you don't have it installed, run: pip install send2trash
try:
    from send2trash import send2trash
except ImportError:
    print("Please install send2trash by running 'pip install send2trash' and try again.")
    sys.exit(1)

def compute_md5(file_path, chunk_size=8192):
    """Compute MD5 hash of a file in chunks to handle large files efficiently."""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                md5_hash.update(data)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return md5_hash.hexdigest()

def find_duplicates_by_size_and_hash(directory, recursive=False):
    """
    Scans the directory for duplicate files.
    
    Files are first grouped by file size. Then, within each size group,
    files are considered duplicates if they have either:
      - the same MD5 hash (i.e. identical content), or 
      - the same file name (basename)
    
    If a duplicate group is found (i.e. more than one file in a group),
    it will be returned as a list of lists.
    
    If recursive=False, only the top-level of the directory is scanned.
    If recursive=True, all subdirectories are scanned.
    """
    size_dict = {}  # { file_size: [file_path1, file_path2, ...] }
    file_count = 0

    print(f"Scanning directory: {directory}")
    if recursive:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                    except Exception as e:
                        print(f"Could not get size for {file_path}: {e}")
                        continue
                    size_dict.setdefault(file_size, []).append(file_path)
                    file_count += 1
    else:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                except Exception as e:
                    print(f"Could not get size for {file_path}: {e}")
                    continue
                size_dict.setdefault(file_size, []).append(file_path)
                file_count += 1

    if file_count == 0:
        print("No files found in the directory.")
        return []

    print(f"Finished scanning. {file_count} file(s) found. Processing potential duplicates...\n")
    
    duplicate_groups = []
    # Process each size group separately.
    for size_val, paths in size_dict.items():
        if len(paths) < 2:
            continue  # Skip groups with only one file
        
        # For each file, compute its MD5 hash and basename.
        file_info = []  # Each element is a tuple: (md5, basename)
        for path in paths:
            file_hash = compute_md5(path)
            base_name = os.path.basename(path)
            file_info.append((file_hash, base_name))
        
        # Use union-find to group files if they share the same MD5 or the same basename.
        n = len(paths)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            rx = find(x)
            ry = find(y)
            if rx != ry:
                parent[ry] = rx
        
        # Compare each pair in the group.
        for i in range(n):
            for j in range(i + 1, n):
                # If files share the same content (md5) OR same name, merge them.
                if file_info[i][0] == file_info[j][0] or file_info[i][1] == file_info[j][1]:
                    union(i, j)
        
        # Group files by their representative parent.
        groups = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(paths[i])
        
        # Only consider groups with more than one file as duplicates.
        for group in groups.values():
            if len(group) > 1:
                duplicate_groups.append(group)

    return duplicate_groups

def is_in_directory(file_path, directory):
    """
    Check if file_path is within the given directory (or its subdirectories).
    Both paths are normalized to absolute paths for comparison.
    """
    file_path = os.path.abspath(file_path)
    directory = os.path.abspath(directory)
    # Ensure the directory path ends with a separator for correct matching.
    directory_with_sep = os.path.join(directory, '')
    return file_path.startswith(directory_with_sep)

def handle_duplicates(duplicate_groups, keep_directory=None):
    """
    For each set of duplicate files:
      - Print the group.
      - Determine which file(s) to keep:
           * If --keep-directory is specified and one or more files are in that directory,
             those files are preserved and duplicates outside are trashed.
           * Otherwise, keep the file that is deeper in the directory hierarchy.
      - Move the files to be removed to Trash.
    Returns the total number of files trashed.
    """
    total_trashed = 0

    def get_depth(fp):
        # Count the number of os.sep in the absolute path as a measure of depth.
        return os.path.abspath(fp).count(os.sep)

    for group in duplicate_groups:
        print("\nFound duplicate set:")
        for file_path in group:
            print(f"  - {file_path}")

        files_to_trash = []
        if keep_directory:
            # Partition the group: files inside the keep-directory vs. others.
            immune = [f for f in group if is_in_directory(f, keep_directory)]
            candidates = [f for f in group if f not in immune]
            if immune:
                print("  Retaining file(s) in the keep-directory; files outside will be trashed.")
                files_to_trash = candidates
            else:
                # No file is in the keep-directory; choose the deepest file.
                keep_file = max(group, key=get_depth)
                print(f"  Retaining the deepest file: {keep_file}")
                files_to_trash = [f for f in group if f != keep_file]
        else:
            # No keep-directory specified; choose the deepest file.
            keep_file = max(group, key=get_depth)
            print(f"  Retaining the deepest file: {keep_file}")
            files_to_trash = [f for f in group if f != keep_file]

        for fp in files_to_trash:
            try:
                send2trash(fp)
                print(f"  Trashed: {fp}")
                total_trashed += 1
            except Exception as e:
                print(f"  Failed to trash {fp}: {e}")

    return total_trashed

def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a directory and remove duplicates based on file size, content, or name.\n\n"
                    "Duplicates are detected if files share the same size and either have identical content (MD5) "
                    "or the same file name.\n\n"
                    "Flags:\n"
                    "  --recursive           Scan subdirectories recursively.\n"
                    "  --keep-directory DIR  Preserve all files within DIR (and its subdirectories).\n"
                    "                        If specified, recursive scanning is automatically enabled.\n",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("directory", help="Directory to scan for duplicates")
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Scan subdirectories recursively (default: False unless --keep-directory is specified)"
    )
    parser.add_argument(
        "--keep-directory",
        type=str,
        help="Directory (and its subdirectories) that should be preserved (untouched).\n"
             "If specified, files within this directory will not be trashed, and --recursive is enabled by default."
    )
    
    # If no arguments are provided, show help.
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        sys.exit(1)

    keep_directory = None
    if args.keep_directory:
        if not os.path.isdir(args.keep_directory):
            print(f"Error: '--keep-directory' value '{args.keep_directory}' is not a valid directory.")
            sys.exit(1)
        keep_directory = os.path.abspath(args.keep_directory)
        # When a keep-directory is specified, we enable recursive scanning.
        args.recursive = True
        print(f"Keep-directory set to: {keep_directory}")

    if args.recursive:
        print("Recursive scanning is enabled.")
    else:
        print("Recursive scanning is disabled. (Scanning only the top-level directory)")

    print("\nStarting duplicate file scan...\n")
    duplicate_groups = find_duplicates_by_size_and_hash(directory, recursive=args.recursive)

    if not duplicate_groups:
        print("No duplicate files found.")
        sys.exit(0)

    trashed_count = handle_duplicates(duplicate_groups, keep_directory=keep_directory)
    print(f"\nDone. Processed duplicate sets and trashed {trashed_count} file(s).")

if __name__ == "__main__":
    main()
