#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
from pathlib import Path
import json

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Loop one or more MP4 files N times or apply a boomerang effect."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--n',
        type=int,
        help="Number of times to loop each MP4 file (must be >=1)."
    )
    group.add_argument(
        '--b',
        type=int,
        help="Number of total forward and backward playthroughs for boomerang effect (must be >=1)."
    )
    parser.add_argument(
        'input_files',
        nargs='+',
        help="One or more input MP4 files to be processed."
    )
    return parser.parse_args()

def validate_arguments(n, b, input_files):
    if n is not None:
        if n < 1:
            print("Error: --n must be an integer >= 1.")
            sys.exit(1)
    if b is not None:
        if b < 1:
            print("Error: --b must be an integer >= 1.")
            sys.exit(1)
    for file in input_files:
        if not os.path.isfile(file):
            print(f"Error: File '{file}' does not exist or is not a file.")
            sys.exit(1)
        if not file.lower().endswith('.mp4'):
            print(f"Error: File '{file}' is not an MP4 file.")
            sys.exit(1)

def has_audio(input_file):
    """
    Uses ffprobe to check if the input file has at least one audio stream.
    Returns True if audio exists, False otherwise.
    """
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=codec_type',
        '-of', 'json',
        input_file
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"ffprobe error for '{input_file}':")
            print(result.stderr)
            return False
        probe = json.loads(result.stdout)
        return any(stream.get('codec_type') == 'audio' for stream in probe.get('streams', []))
    except Exception as e:
        print(f"An exception occurred while probing '{input_file}': {e}")
        return False

def loop_mp4_file(input_file, n):
    input_path = Path(input_file)
    output_filename = f"{input_path.stem}_looped{n}{input_path.suffix}"
    output_path = input_path.parent / output_filename

    # Calculate the number of additional loops.
    stream_loop = n - 1

    print(f"Processing '{input_file}' -> '{output_path}' with {n} loops.")

    # Build the ffmpeg command.
    command = [
        'ffmpeg',
        '-y',  # Overwrite output files without asking.
        '-stream_loop', str(stream_loop),
        '-i', str(input_path),
        '-c', 'copy',
        str(output_path)
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"Error processing '{input_file}':")
            print(result.stderr)
            return False

        print(f"Successfully created '{output_path}'.")
        return True

    except Exception as e:
        print(f"An exception occurred while processing '{input_file}': {e}")
        return False

def boomerang_mp4_file(input_file, n):
    input_path = Path(input_file)
    output_filename = f"{input_path.stem}_boomerang{n}{input_path.suffix}"
    output_path = input_path.parent / output_filename

    print(f"Processing '{input_file}' -> '{output_path}' with boomerang effect ({n} playthroughs).")

    # Check if the input has audio.
    audio_exists = has_audio(input_file)

    if audio_exists:
        # Construct the filter_complex for both video and audio (reverse both).
        filter_complex = "[0:v]reverse[vrev]; [0:a]areverse[arev]; "

        # Build stream list.
        stream_list = []
        for i in range(n):
            if i % 2 == 0:
                # Forward playthrough.
                stream_list.append("[0:v][0:a]")
            else:
                # Reversed playthrough.
                stream_list.append("[vrev][arev]")
        streams_concat = ''.join(stream_list)
        filter_complex += f"{streams_concat}concat=n={n}:v=1:a=1[outv][outa]"

        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking.
            '-i', str(input_path),
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '[outa]',
            str(output_path)
        ]
    else:
        # Construct the filter_complex for video only.
        filter_complex = "[0:v]reverse[vrev]; "

        stream_list = []
        for i in range(n):
            if i % 2 == 0:
                stream_list.append("[0:v]")
            else:
                stream_list.append("[vrev]")
        streams_concat = ''.join(stream_list)
        filter_complex += f"{streams_concat}concat=n={n}:v=1:a=0[outv]"

        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking.
            '-i', str(input_path),
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-c:a', 'copy',  # Attempt to copy audio if exists.
            str(output_path)
        ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"Error processing '{input_file}' with boomerang effect:")
            print(result.stderr)
            return False

        print(f"Successfully created '{output_path}'.")
        return True

    except Exception as e:
        print(f"An exception occurred while processing '{input_file}' with boomerang effect: {e}")
        return False

def archive_file(input_file):
    """
    Moves the original file into an "archive" subfolder within its directory.
    """
    input_path = Path(input_file).resolve()
    archive_dir = input_path.parent / "archive"
    try:
        archive_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error creating archive directory '{archive_dir}': {e}")
        return
    destination = archive_dir / input_path.name
    try:
        input_path.rename(destination)
        print(f"Moved '{input_path}' to '{destination}'.")
    except Exception as e:
        print(f"Error moving '{input_path}' to archive: {e}")

def main():
    args = parse_arguments()
    n = args.n
    b = args.b
    input_files = args.input_files

    validate_arguments(n, b, input_files)

    for input_file in input_files:
        if n is not None:
            success = loop_mp4_file(input_file, n)
        elif b is not None:
            success = boomerang_mp4_file(input_file, b)
        else:
            print("Error: Either --n or --b must be specified.")
            sys.exit(1)
        
        if success:
            # Move the original input file to the archive folder.
            archive_file(input_file)
        else:
            print(f"Failed to process '{input_file}'. Continuing with next file.")

if __name__ == "__main__":
    main()
