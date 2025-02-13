#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
import random
import shutil
import json

def check_ffmpeg():
    """Check if ffmpeg and ffprobe are installed."""
    for cmd in ['ffmpeg', 'ffprobe']:
        try:
            subprocess.run([cmd, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print(f"Error: {cmd} is not installed or not found in PATH.")
            sys.exit(1)

def archive_files(file_list):
    """Move input files to the 'archive' folder in their respective directories."""
    for file_path in file_list:
        dir_name = os.path.dirname(file_path) or '.'  # Handle files in current directory
        archive_dir = os.path.join(dir_name, 'archive')
        
        # Create the archive directory if it doesn't exist
        os.makedirs(archive_dir, exist_ok=True)
        
        # Define the destination path
        destination = os.path.join(archive_dir, os.path.basename(file_path))
        
        try:
            shutil.move(file_path, destination)
            print(f"Archived {file_path} to {destination}")
        except Exception as e:
            print(f"Error archiving {file_path}: {e}")

def get_video_resolution(file_path):
    """Retrieve the resolution of a video using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'json',
        file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        data = json.loads(result.stdout)
        width = data['streams'][0]['width']
        height = data['streams'][0]['height']
        return width, height
    except (subprocess.CalledProcessError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Error retrieving resolution for {file_path}: {e}")
        sys.exit(1)

def determine_common_resolution(file_list):
    """Determine the maximum width and height among all input videos."""
    max_width = 0
    max_height = 0
    for file in file_list:
        width, height = get_video_resolution(file)
        if width > max_width:
            max_width = width
        if height > max_height:
            max_height = height
    return max_width, max_height

def reencode_videos(file_list, target_width, target_height, temp_dir):
    """Re-encode all videos to the target resolution and store them in temp_dir."""
    reencoded_files = []
    for idx, file in enumerate(file_list):
        output_path = os.path.join(temp_dir, f"reencoded_{idx}.mp4")
        cmd = [
            'ffmpeg', '-i', file,
            '-vf', f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
            '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
            '-c:a', 'aac', '-b:a', '192k',
            '-y',  # Overwrite without asking
            output_path
        ]
        print(f"Re-encoding {file} to resolution {target_width}x{target_height}...")
        try:
            subprocess.run(cmd, check=True)
            reencoded_files.append(output_path)
            print(f"Re-encoded {file} successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error re-encoding {file}: {e}")
            sys.exit(1)
    return reencoded_files

def main():
    parser = argparse.ArgumentParser(description='Concatenate multiple MP4 files into one, handling different dimensions.')
    parser.add_argument('files', metavar='file', type=str, nargs='+',
                        help='Input MP4 files to concatenate')
    args = parser.parse_args()

    check_ffmpeg()

    # Sort files alphanumerically
    file_list = sorted(args.files)

    # Verify that all files exist
    for filename in file_list:
        if not os.path.isfile(filename):
            print(f"Error: File not found - {filename}")
            sys.exit(1)

    # Determine output file name based on the first input file
    first_file = file_list[0]
    dirname = os.path.dirname(first_file) or '.'  # Handle files in current directory
    basename = os.path.basename(first_file)
    root, ext = os.path.splitext(basename)
    
    # Remove the last 25 characters before the extension
    if len(root) > 25:
        new_root = root[:-25]
    else:
        new_root = root  # Avoid negative indexing if root is shorter than 25 chars

    # Generate a random four-digit number
    randnums = random.randint(0, 9999)
    random_str = f"{randnums:04d}"  # Format as four digits, padding with zeros if needed

    # Append the random number to the new root
    output_root = new_root + '_joined_' + random_str
    output_filename = os.path.join(dirname, output_root + ext)

    # Create a temporary directory to store re-encoded videos
    with tempfile.TemporaryDirectory() as temp_dir:
        # Determine common resolution
        print("Determining common resolution for all videos...")
        target_width, target_height = determine_common_resolution(file_list)
        print(f"Common resolution set to {target_width}x{target_height}.")

        # Re-encode all videos to the common resolution
        reencoded_files = reencode_videos(file_list, target_width, target_height, temp_dir)

        # Create a temporary file to hold the list of re-encoded files
        with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
            for filename in reencoded_files:
                # Escape single quotes in filenames
                escaped_filename = filename.replace("'", "'\\''")
                temp_file.write(f"file '{escaped_filename}'\n")
            temp_filename = temp_file.name

        # Construct and run the ffmpeg concat command
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', temp_filename, '-c', 'copy', output_filename
        ]
        try:
            print(f"Concatenating videos into {output_filename}...")
            subprocess.run(cmd, check=True)
            print(f"Successfully created {output_filename}")
            
            # Archive the original input files after successful concatenation
            archive_files(file_list)
        except subprocess.CalledProcessError as e:
            print(f"Error during ffmpeg execution: {e}")
            sys.exit(1)
        finally:
            # Clean up the temporary concat list file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

if __name__ == '__main__':
    main()
