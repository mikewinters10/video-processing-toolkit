#!/usr/bin/env python3

import subprocess
import argparse
import os
import shutil  # Added for file operations

def parse_time_string(time_str):
    """
    Parse a time string in one of two formats:
      1) mm:ss.dd (minutes:seconds[.fraction])
      2) ss.dd (just seconds[.fraction])
    """
    # If there's no colon, interpret the entire string as seconds.
    if ':' not in time_str:
        try:
            return float(time_str)
        except ValueError as e:
            print(f"Error parsing time string '{time_str}': {e}")
            return None
    else:
        # Parse in the mm:ss.dd format
        try:
            mm_ss = time_str.split(':')
            if len(mm_ss) != 2:
                raise ValueError("Time format should be mm:ss.dd")
            minutes = int(mm_ss[0])
            seconds_fraction = mm_ss[1]
            if '.' in seconds_fraction:
                seconds, fraction = seconds_fraction.split('.')
                seconds = int(seconds)
                fraction = int(fraction)
                fraction = fraction / (10 ** len(str(fraction)))
            else:
                seconds = int(seconds_fraction)
                fraction = 0
            total_seconds = minutes * 60 + seconds + fraction
            return total_seconds
        except Exception as e:
            print(f"Error parsing time string '{time_str}': {e}")
            return None

def format_time_for_filename(time_seconds):
    minutes = int(time_seconds // 60)
    seconds = int(time_seconds % 60)
    hundredths = int(round((time_seconds - int(time_seconds)) * 100))
    return f"{minutes:02d}{seconds:02d}{hundredths:02d}"

def get_video_dimensions(input_file):
    ffprobe_command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0:s=x', input_file
    ]
    result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"Error getting video dimensions for '{input_file}': {result.stderr}")
        return None, None

    output = result.stdout.strip()
    if 'x' in output:
        dimensions = output.split('x')[:2]
        try:
            width, height = map(int, dimensions)
            return width, height
        except ValueError:
            print(f"Error parsing video dimensions from ffprobe output: '{output}'")
            return None, None
    else:
        print(f"Unexpected output format from ffprobe for '{input_file}': '{output}'")
        return None, None

def get_video_duration(input_file):
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
        print(f"Error getting duration of video '{input_file}': {result.stderr}")
        return None
    duration_str = result.stdout.strip()
    try:
        duration = float(duration_str)
        return duration
    except ValueError:
        print(f"Error parsing duration '{duration_str}' for video '{input_file}'")
        return None

def generate_crop_filter(input_file, left, right, top, bottom):
    if left == 0.0 and right == 0.0 and top == 0.0 and bottom == 0.0:
        return None

    width, height = get_video_dimensions(input_file)
    if width is None or height is None:
        return None

    # Ensure crop percentages are valid
    if (left + right >= 1.0) or (top + bottom >= 1.0):
        print(f"Invalid crop percentages for '{input_file}': left+right or top+bottom exceed 100% of video width or height.")
        return None

    # Calculate crop dimensions based on percentages
    crop_width = width - int((left + right) * width)
    crop_height = height - int((top + bottom) * height)
    x_offset = int(left * width)
    y_offset = int(top * height)

    # Ensure crop dimensions are positive
    if crop_width <= 0 or crop_height <= 0:
        print(f"Calculated crop dimensions are invalid (non-positive) for '{input_file}': crop_width={crop_width}, crop_height={crop_height}.")
        return None

    crop_filter = f"crop={crop_width}:{crop_height}:{x_offset}:{y_offset}"
    return crop_filter

def has_audio_stream(input_file):
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=index',
        '-of', 'csv=p=0',
        input_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return False
    output = result.stdout.strip()
    return output != ''

def generate_output_filename(input_file, left, right, top, bottom, start_time=None, end_time=None, remove_segment=False):
    # Extract the directory, file name, and extension
    directory = os.path.dirname(input_file)
    base_name, ext = os.path.splitext(os.path.basename(input_file))

    # Create a suffix based on the cropping parameters
    suffix_parts = []
    if left > 0:
        suffix_parts.append(f"l{int(left*100)}")
    if right > 0:
        suffix_parts.append(f"r{int(right*100)}")
    if top > 0:
        suffix_parts.append(f"t{int(top*100)}")
    if bottom > 0:
        suffix_parts.append(f"b{int(bottom*100)}")

    # Include start and end times in the suffix
    if start_time is not None:
        suffix_parts.append(f"s{format_time_for_filename(start_time)}")
    if end_time is not None:
        suffix_parts.append(f"e{format_time_for_filename(end_time)}")

    if remove_segment:
        suffix_parts.append("cut")

    # Join suffix parts to form the full suffix
    suffix = "_".join(suffix_parts) if suffix_parts else "no_crop"

    # Return the new output file path with suffix in the same directory
    return os.path.join(directory, f"{base_name}_{suffix}{ext}")

def crop_video(input_file, left, right, top, bottom, start_time=None, end_time=None):
    # Generate output filename based on input and crop parameters
    output_file = generate_output_filename(input_file, left, right, top, bottom, start_time, end_time)

    # Generate crop filter if necessary
    crop_filter = generate_crop_filter(input_file, left, right, top, bottom)

    # Construct the ffmpeg command
    ffmpeg_command = ['ffmpeg', '-i', input_file]

    # Add start and end times if provided
    if start_time is not None:
        ffmpeg_command += ['-ss', str(start_time)]
    if end_time is not None:
        ffmpeg_command += ['-to', str(end_time)]

    # Add crop filter if specified
    filter_chain = []
    if crop_filter:
        filter_chain.append(crop_filter)

    output_ext = os.path.splitext(output_file)[1].lower()

    if output_ext == '.gif':
        # For GIFs, use palette generation for better quality
        palette_file = os.path.join(os.path.dirname(output_file), 'palette.png')

        # First pass: generate palette
        palettegen_command = ['ffmpeg', '-i', input_file]
        if start_time is not None:
            palettegen_command += ['-ss', str(start_time)]
        if end_time is not None:
            palettegen_command += ['-to', str(end_time)]
        if filter_chain:
            palettegen_command += ['-vf', ','.join(filter_chain + ['palettegen'])]
        else:
            palettegen_command += ['-vf', 'palettegen']
        palettegen_command += ['-y', palette_file]

        print(f"Generating palette with command: {' '.join(palettegen_command)}")
        result = subprocess.run(palettegen_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"Error generating palette for GIF '{input_file}': {result.stderr}")
            return None

        # Second pass: create GIF using the palette
        ffmpeg_command = ['ffmpeg', '-i', input_file, '-i', palette_file]
        if start_time is not None:
            ffmpeg_command += ['-ss', str(start_time)]
        if end_time is not None:
            ffmpeg_command += ['-to', str(end_time)]
        filter_chain.append('paletteuse')
        ffmpeg_command += ['-filter_complex', ','.join(filter_chain)]
        ffmpeg_command += ['-y', output_file]

        print(f"Creating GIF with command: {' '.join(ffmpeg_command)}")
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print(f"GIF cropped successfully. Saved as '{output_file}'")
        else:
            print(f"Error cropping GIF '{input_file}': {result.stderr}")

        # Clean up palette file
        if os.path.exists(palette_file):
            os.remove(palette_file)
    else:
        # Determine if the file has an audio stream
        audio_exists = has_audio_stream(input_file)
        if audio_exists:
            ffmpeg_command += ['-c:a', 'aac']
        else:
            ffmpeg_command += ['-an']  # No audio

        if filter_chain:
            ffmpeg_command += ['-vf', ','.join(filter_chain)]

        ffmpeg_command += ['-c:v', 'libx264', '-y', output_file]

        # Run the ffmpeg command to crop the video
        print(f"Running ffmpeg command: {' '.join(ffmpeg_command)}")
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print(f"Video cropped successfully. Saved as '{output_file}'")
        else:
            print(f"Error cropping video '{input_file}': {result.stderr}")

    return output_file if os.path.exists(output_file) else None  # Return the output file path if successful

def remove_segment(input_file, left, right, top, bottom, start_time, end_time):
    # Generate output filename
    output_file = generate_output_filename(input_file, left, right, top, bottom, start_time, end_time, remove_segment=True)

    # Generate crop filter if necessary
    crop_filter = generate_crop_filter(input_file, left, right, top, bottom)

    # Determine if there is an audio stream
    audio_exists = has_audio_stream(input_file)

    # Build the filter_complex
    filter_complex = []

    # Start building the filter graph for video
    if crop_filter:
        filter_complex.append(f"[0:v]{crop_filter},split=2[v1][v2]")
    else:
        filter_complex.append(f"[0:v]split=2[v1][v2]")

    filter_complex.append(f"[v1]trim=0:{start_time},setpts=PTS-STARTPTS[v1a]")
    filter_complex.append(f"[v2]trim=start={end_time},setpts=PTS-STARTPTS[v2a]")

    if audio_exists:
        # Build the filter graph for audio
        filter_complex.append(f"[0:a]asplit=2[a1][a2]")
        filter_complex.append(f"[a1]atrim=0:{start_time},asetpts=PTS-STARTPTS[a1a]")
        filter_complex.append(f"[a2]atrim=start={end_time},asetpts=PTS-STARTPTS[a2a]")
        # Concatenate video and audio streams
        filter_complex.append(f"[v1a][a1a][v2a][a2a]concat=n=2:v=1:a=1[outv][outa]")
    else:
        # Concatenate video streams without audio
        filter_complex.append(f"[v1a][v2a]concat=n=2:v=1:a=0[outv]")

    filter_complex_str = ';'.join(filter_complex)

    # Build ffmpeg command
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_file,
        '-filter_complex', filter_complex_str,
        '-map', '[outv]',
    ]

    if audio_exists:
        ffmpeg_command += ['-map', '[outa]']
        ffmpeg_command += ['-c:a', 'aac']
    else:
        ffmpeg_command += ['-an']  # No audio

    ffmpeg_command += ['-c:v', 'libx264', '-y', output_file]

    # Run ffmpeg command
    print(f"Running ffmpeg command: {' '.join(ffmpeg_command)}")
    result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode == 0:
        print(f"Segment removed successfully. Saved as '{output_file}'")
    else:
        print(f"Error removing segment from video '{input_file}': {result.stderr}")

    return output_file if os.path.exists(output_file) else None  # Return the output file path if successful

def create_archive_directory(file_directory):
    archive_dir = os.path.join(file_directory, "archive")
    if not os.path.exists(archive_dir):
        try:
            os.makedirs(archive_dir)
            print(f"Created archive directory at '{archive_dir}'.")
        except Exception as e:
            print(f"Error creating archive directory '{archive_dir}': {e}")
            return None
    else:
        print(f"Archive directory already exists at '{archive_dir}'.")
    return archive_dir

def move_files_to_archive(input_file, archive_dir):
    try:
        # Move the original input file
        shutil.move(input_file, archive_dir)
        print(f"Moved '{input_file}' to '{archive_dir}'.")
    except Exception as e:
        print(f"Error moving '{input_file}' to archive: {e}")

    # Construct the screen image filename
    base_name, ext = os.path.splitext(input_file)
    screen_file = f"{base_name}-screen.jpg"

    if os.path.exists(screen_file):
        try:
            shutil.move(screen_file, archive_dir)
            print(f"Moved '{screen_file}' to '{archive_dir}'.")
        except Exception as e:
            print(f"Error moving '{screen_file}' to archive: {e}")
    else:
        print(f"No corresponding screen image '{screen_file}' found to move.")

def run_grid_creator(new_file):
    try:
        subprocess.run(['./grid_creator.py', '9', '--k', new_file], check=True)
        print(f"Successfully executed grid_creator.py on '{new_file}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error running grid_creator.py on '{new_file}': {e}")
    except FileNotFoundError:
        print(f"grid_creator.py not found in the current directory.")

def main():
    parser = argparse.ArgumentParser(description="Crop multiple videos by a percentage using ffmpeg.")
    parser.add_argument("input_files", nargs='+', help="Paths to the input video files")
    parser.add_argument("--l", type=float, default=0.0, help="Percentage to crop from the left (0.0-1.0)")
    parser.add_argument("--r", type=float, default=0.0, help="Percentage to crop from the right (0.0-1.0)")
    parser.add_argument("--t", type=float, default=0.0, help="Percentage to crop from the top (0.0-1.0)")
    parser.add_argument("--b", type=float, default=0.0, help="Percentage to crop from the bottom (0.0-1.0)")
    parser.add_argument("--s", help="Start time (e.g., 10.02 for 10.02s or 00:10.02 for 10.02s)")
    parser.add_argument("--e", help="End time (e.g., 45.5 for 45.5s or 00:45.5 for 45.5s)")
    parser.add_argument("--c", action='store_true', help="Remove the segment between --s and --e and concatenate the rest.")
    # Changed flag name from --no-screens to --screens
    parser.add_argument("--screens", action='store_true',
                        help="If provided, create the screenshot grid (via grid_creator.py) as is done presently.")

    args = parser.parse_args()

    # Process each input file
    for input_file in args.input_files:
        # Ensure the input file exists
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' does not exist.")
            continue

        print(f"\nStarting processing for file: {input_file}")

        # Parse start and end times if provided
        start_time = None
        if args.s:
            start_time = parse_time_string(args.s)
            if start_time is None:
                print(f"Invalid start time format: {args.s}")
                continue

        end_time = None
        if args.e:
            end_time = parse_time_string(args.e)
            if end_time is None:
                print(f"Invalid end time format: {args.e}")
                continue

        # Ensure that start time is less than end time
        if start_time is not None and end_time is not None and start_time >= end_time:
            print("Error: Start time must be less than end time.")
            continue

        output_file = None
        if args.c:
            # Ensure both start_time and end_time are provided
            if start_time is None or end_time is None:
                print("Error: Both start time (--s) and end time (--e) must be provided when using --c.")
                continue
            output_file = remove_segment(input_file, args.l, args.r, args.t, args.b, start_time, end_time)
        else:
            # Use the provided crop percentages or the defaults (0.0 if not provided)
            output_file = crop_video(input_file, args.l, args.r, args.t, args.b, start_time, end_time)

        if output_file:
            # Determine the directory of the input file
            input_dir = os.path.dirname(os.path.abspath(input_file))
            # Create archive directory in the input file's directory
            archive_dir = create_archive_directory(input_dir)
            if archive_dir is None:
                print(f"Failed to create or access the archive directory for '{input_file}'. Skipping archiving and grid creation.")
                continue

            # Move original files to archive
            move_files_to_archive(input_file, archive_dir)

            # Run grid_creator.py if the --screens flag is provided.
            if args.screens:
                run_grid_creator(output_file)
        else:
            print(f"Processing failed for '{input_file}'. Skipping archiving and grid creation.")

if __name__ == "__main__":
    main()
