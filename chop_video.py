#!/usr/bin/env python3

import subprocess
import argparse
import os


def parse_time_string(time_str):
    """
    Parse a time string that can be:
      - "10.46"      ->  0:10.46   (10.46 seconds)
      - "01:10.46"   ->  1:10.46   (1 minute, 10.46 seconds)
      - "5:15"       ->  5:15.00   (5 minutes, 15 seconds)
    """
    try:
        parts = time_str.split(':')
        if len(parts) == 1:
            # No colon -> entire string is seconds(.fraction)
            minutes = 0
            seconds_fraction = parts[0]
        elif len(parts) == 2:
            # One colon -> mm:ss(.fraction)
            minutes_str, seconds_fraction = parts
            minutes = int(minutes_str)
        else:
            raise ValueError("Invalid time format: too many colons.")

        if '.' in seconds_fraction:
            seconds_str, fraction_str = seconds_fraction.split('.')
            seconds = int(seconds_str)
            fraction = int(fraction_str) / (10 ** len(fraction_str))
        else:
            seconds = int(seconds_fraction)
            fraction = 0

        return minutes * 60 + seconds + fraction

    except Exception as e:
        raise ValueError(f"Error parsing time string '{time_str}': {e}")


def get_video_duration(input_file):
    """
    Use ffprobe to get the duration (in seconds) of the input_file.
    """
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error getting duration of video '{input_file}': {result.stderr}")

    try:
        return float(result.stdout.strip())
    except ValueError as e:
        raise ValueError(f"Error parsing duration of video '{input_file}': {e}")


def format_time_for_filename(time_seconds):
    """
    Convert float seconds into a string like '003005' for 3m 5.05s.
    """
    minutes = int(time_seconds // 60)
    seconds = int(time_seconds % 60)
    hundredths = int(round((time_seconds - int(time_seconds)) * 100))
    return f"{minutes:02d}{seconds:02d}{hundredths:02d}"


def generate_output_filename_split(input_file, start_time, end_time, segment_number):
    """
    Generate an output filename for each segment, embedding the start/end times,
    and place it in the same directory as the input file.
    """
    dir_name = os.path.dirname(input_file)
    base_name, ext = os.path.splitext(os.path.basename(input_file))
    start_str = format_time_for_filename(start_time)
    end_str = format_time_for_filename(end_time)
    output_file = f"{base_name}_part{segment_number}_{start_str}_{end_str}{ext}"
    return os.path.join(dir_name, output_file)


def split_video(input_file, timestamps, padding):
    """
    Split the input_file into segments at the given timestamps.
    Now, each timestamp marks the start of a padding period.
    The segment ends at the timestamp, and the next segment begins after adding the padding.
    """
    duration = get_video_duration(input_file)
    sorted_ts = sorted(timestamps)

    # Determine segment boundaries based on the new logic
    segments = []

    # First segment: start at 0, end at first timestamp (if exists)
    if sorted_ts:
        segments.append((0, sorted_ts[0]))
    else:
        segments.append((0, duration))

    # Middle segments: start after padding from previous timestamp, end at current timestamp
    for i in range(1, len(sorted_ts)):
        start = sorted_ts[i - 1] + padding
        end = sorted_ts[i]
        segments.append((start, end))

    # Last segment: start after padding from last timestamp, go until the end of video
    if sorted_ts:
        segments.append((sorted_ts[-1] + padding, duration))

    # Process each segment with ffmpeg
    for i, (segment_start, segment_end) in enumerate(segments):
        segment_duration = segment_end - segment_start

        if segment_duration <= 0:
            print(f"Warning: segment {i + 1} would have non-positive duration. Skipped.")
            continue

        output_file = generate_output_filename_split(input_file, segment_start, segment_end, i + 1)

        ffmpeg_command = [
            'ffmpeg',
            '-i', input_file,
            '-ss', str(segment_start),
            '-t', str(segment_duration),
            '-c:v', 'libx264',
            '-an',       # Currently discards audio; remove or modify if you need audio
            '-y',        # Overwrite output file
            output_file
        ]

        print(f"\nProcessing segment {i + 1}: start={segment_start}, end={segment_end}")
        print("Running ffmpeg command:", " ".join(ffmpeg_command))

        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print(f"Segment {i + 1} saved as '{output_file}'")
        else:
            print(f"Error processing segment {i + 1}: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Split a video into segments based on timestamps, with optional padding.")
    parser.add_argument("--k", nargs='+', required=True,
                        help="List of timestamps (e.g. 00:10.02, 10.02, etc.) to split the video.")
    parser.add_argument("--p", type=float, default=0.0,
                        help="Padding in seconds after each cut boundary before the next segment begins.")
    # Accept multiple input video files instead of just one
    parser.add_argument("input_files", nargs='+', help="Path(s) to the input video file(s).")

    args = parser.parse_args()
    input_files = args.input_files
    timestamps = [parse_time_string(ts) for ts in args.k]
    padding = args.p

    for input_file in input_files:
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' does not exist.")
            continue

        print(f"Starting splitting for file: {input_file}")
        print(f"Using timestamps: {args.k}")
        if padding > 0.0:
            print(f"Applying {padding}s of padding after each specified timestamp.")

        split_video(input_file, timestamps, padding)


if __name__ == "__main__":
    main()
