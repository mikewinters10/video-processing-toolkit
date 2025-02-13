#!/usr/bin/env python3
import sys
import os
import subprocess

def get_duration(file_path):
    """
    Returns the duration of the video file in seconds (as a float) using ffprobe.
    """
    try:
        # Build the ffprobe command.
        # This command returns just the duration in seconds.
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        # Run the command and capture the output.
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return float(duration_str)
        else:
            print(f"Warning: Could not determine duration for {file_path}.")
            return 0.0
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path}: {e.stderr}")
        return 0.0
    except Exception as e:
        print(f"Unexpected error with {file_path}: {e}")
        return 0.0

def format_total_duration(total_seconds):
    """
    Formats the total duration (in seconds) into a human‐readable string.
    
    - If total time is less than 60 seconds, shows only seconds.
    - If total time is at least 60 seconds but less than 1 hour, shows minutes and seconds.
    - Otherwise, shows hours, minutes, and seconds.
    """
    total_seconds = int(round(total_seconds))
    
    if total_seconds < 60:
        # Less than 1 minute: only seconds.
        return f"{total_seconds} seconds"
    elif total_seconds < 3600:
        # At least 1 minute but less than 1 hour.
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes} minutes and {seconds} seconds"
    else:
        # 1 hour or more.
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours {minutes} minutes and {seconds} seconds"

def main():
    # Check that at least one file was provided.
    if len(sys.argv) < 2:
        print("Usage: {} file1.mp4 file2.mp4 ...".format(os.path.basename(sys.argv[0])))
        sys.exit(1)
    
    total_duration = 0.0
    for file_path in sys.argv[1:]:
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            continue
        duration = get_duration(file_path)
        print(f"{file_path}: {duration:.2f} seconds")
        total_duration += duration

    formatted = format_total_duration(total_duration)
    print(f"Input Files have total duration of {formatted}")

if __name__ == '__main__':
    main()
