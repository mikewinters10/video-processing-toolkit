#!/usr/bin/env python3

import sys
import os
import shutil
import glob

def get_root_name(filename):
    """
    Given a filename, returns the base 'root' part (without extension
    and without '-screen' or '-screens' suffix if present).

    Examples:
      - file1.mp4             -> file1
      - file1-screen.jpg      -> file1
      - file1-screens.jpeg    -> file1
    """
    base = os.path.basename(filename)   # e.g. file1-screen.jpg
    name, ext = os.path.splitext(base)  # e.g. name='file1-screen', ext='.jpg'
    for suffix in ('-screen', '-screens'):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file1> [file2] [file3] ...")
        sys.exit(1)
    
    for arg in sys.argv[1:]:
        # Convert the supplied argument to an absolute path
        input_path = os.path.abspath(arg)
        
        if not os.path.exists(input_path):
            print(f"Warning: {arg} does not exist. Skipping.")
            continue

        # Identify the directory of the input file
        directory = os.path.dirname(input_path)      # e.g. /home/user/videos
        base_dir_name = os.path.basename(directory)  # e.g. videos

        # Figure out the root name (strip extension and -screen/-screens)
        root_name = get_root_name(input_path)

        # Prepare the destination subdirectories within the same directory
        moved_dir = os.path.join(directory, base_dir_name + "-moved")
        screens_dir = os.path.join(directory, base_dir_name + "-screens")
        os.makedirs(moved_dir, exist_ok=True)
        os.makedirs(screens_dir, exist_ok=True)

        # 1) Move the MP4 if it exists
        mp4_path = os.path.join(directory, root_name + ".mp4")
        if os.path.exists(mp4_path):
            dest_path = os.path.join(moved_dir, os.path.basename(mp4_path))
            if os.path.abspath(mp4_path) != os.path.abspath(dest_path):
                print(f"Moving {mp4_path} -> {dest_path}")
                shutil.move(mp4_path, dest_path)
            else:
                print(f"Skipping {mp4_path} (already in destination).")

        # 2) Move all "screen" files, i.e. <root_name>-screen.* or <root_name>-screens.*
        screen_patterns = [
            os.path.join(directory, root_name + "-screen.*"),
            os.path.join(directory, root_name + "-screens.*")
        ]
        
        for pattern in screen_patterns:
            for screen_file in glob.glob(pattern):
                dest_path = os.path.join(screens_dir, os.path.basename(screen_file))
                if os.path.abspath(screen_file) != os.path.abspath(dest_path):
                    print(f"Moving {screen_file} -> {dest_path}")
                    shutil.move(screen_file, dest_path)
                else:
                    print(f"Skipping {screen_file} (already in destination).")

if __name__ == "__main__":
    main()