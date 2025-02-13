#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import shutil
from send2trash import send2trash
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automatically split MP4 files into segments based on scene transitions using PySceneDetect."
    )
    parser.add_argument(
        "input_files",
        nargs='+',
        help="Path(s) to the input MP4 file(s). You can specify multiple files separated by spaces."
    )
    parser.add_argument(
        "--g",
        type=float,
        default=30.0,
        help=(
            "Scene detection threshold for PySceneDetect's ContentDetector (default: 30.0). "
            "Lower values detect more scenes. Typical range: 0.0 to 100.0."
        )
    )
    parser.add_argument(
        "--p",
        type=float,
        default=0.0,
        help="Padding in seconds around each transition (default: 0.0)."
    )
    return parser.parse_args()

def detect_scenes(input_file, threshold):
    """
    Detect scene boundaries using PySceneDetect.

    :param input_file: Path to the input video file.
    :param threshold: Scene detection threshold.
    :return: List of tuples representing (start_time, end_time) for each scene in seconds.
    """
    video_manager = VideoManager([input_file])
    scene_manager = SceneManager()
    detector = ContentDetector(threshold=threshold)
    detector.min_scene_len = 2  # Set the minimum scene length directly on the detector
    scene_manager.add_detector(detector)

    # Optional: Set downscale factor for faster processing
    video_manager.set_downscale_factor()

    try:
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()
        # Convert scene list to list of (start, end) times in seconds
        scene_times = [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]
        return scene_times
    finally:
        video_manager.release()

def get_video_duration(input_file):
    """
    Retrieve the total duration of the video in seconds using ffprobe.

    :param input_file: Path to the input video file.
    :return: Duration in seconds.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_file
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving video duration for '{input_file}': {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        print(f"Error: Unable to parse video duration for '{input_file}'.", file=sys.stderr)
        sys.exit(1)

def get_scene_boundaries(scenes, video_duration):
    """
    Define scene boundaries based on scene start and end times.

    :param scenes: List of tuples (start_time, end_time) for each scene.
    :param video_duration: Total duration of the video in seconds.
    :return: List of tuples (start, end) for each scene.
    """
    return scenes  # Each scene is already a (start, end) tuple

def apply_padding(scene_boundaries, padding, video_duration):
    """
    Apply padding around each scene boundary to define segment boundaries.

    For each scene:
        - Add half of the padding before the scene starts.
        - Add half of the padding after the scene ends.

    Ensure that segments do not overlap and do not exceed video boundaries.

    :param scene_boundaries: List of tuples (start, end) for each scene.
    :param padding: Total padding in seconds to apply around each scene.
    :param video_duration: Total duration of the video in seconds.
    :return: List of tuples (start, end) for each segment with padding.
    """
    half_padding = padding / 2
    segments = []
    previous_segment_end = 0.0

    for idx, (scene_start, scene_end) in enumerate(scene_boundaries):
        # Calculate padded start and end
        padded_start = scene_start - half_padding
        padded_end = scene_end + half_padding

        # Clamp the padded times to the video duration boundaries
        padded_start = max(padded_start, 0.0)
        padded_end = min(padded_end, video_duration)

        # Ensure no overlap with the previous segment
        if padded_start < previous_segment_end:
            padded_start = previous_segment_end

        # Ensure that the segment has a positive duration
        if padded_end > padded_start:
            segments.append((padded_start, padded_end))
            previous_segment_end = padded_end
        else:
            print(f"Warning: Segment {idx + 1} has non-positive duration and will be skipped.", file=sys.stderr)

    return segments

def split_video(input_file, segments, output_dir):
    """
    Split the video into segments using ffmpeg with re-encoding for frame-accurate cuts.

    :param input_file: Path to the input video file.
    :param segments: List of tuples representing (start, end) times for each segment.
    :param output_dir: Directory where the segments will be saved.
    """
    base_name, ext = os.path.splitext(os.path.basename(input_file))
    os.makedirs(output_dir, exist_ok=True)

    for idx, (start, end) in enumerate(segments, start=1):
        duration = end - start
        output_file = os.path.join(output_dir, f"{base_name}_segment_{idx:03d}{ext}")

        # FFmpeg command for re-encoding to ensure frame-accurate cuts
        ffmpeg_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", input_file,
            "-ss", f"{start}",
            "-t", f"{duration}",
            "-c:v", "libx264",        # Video codec
            "-preset", "fast",        # Encoding speed/quality
            "-crf", "18",             # Quality (lower is better)
            "-c:a", "aac",            # Audio codec
            "-b:a", "192k",           # Audio bitrate
            "-avoid_negative_ts", "make_zero",
            output_file
        ]

        print(f"Creating segment {idx}: start={start:.3f}s, duration={duration:.3f}s -> {output_file}")
        try:
            subprocess.run(ffmpeg_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error creating segment {idx}: {e}", file=sys.stderr)

def move_original(input_file, transitions_dir):
    """
    Move the original input file into the transitions directory.

    :param input_file: Path to the input video file.
    :param transitions_dir: Path to the 'transitions' directory.
    """
    destination = os.path.join(transitions_dir, os.path.basename(input_file))
    try:
        shutil.move(input_file, destination)
        print(f"Moved original file to {destination}")
    except Exception as e:
        print(f"Warning: Could not move the original file '{input_file}': {e}", file=sys.stderr)

def move_screen_jpg(input_file):
    """
    Check for a corresponding '-screen.jpg' file and move it to the Trash if it exists.

    :param input_file: Path to the input video file.
    """
    base_name, _ = os.path.splitext(os.path.basename(input_file))
    dir_name = os.path.dirname(os.path.abspath(input_file))
    screen_jpg = os.path.join(dir_name, f"{base_name}-screen.jpg")

    if os.path.isfile(screen_jpg):
        try:
            send2trash(screen_jpg)
            print(f"Moved '{screen_jpg}' to Trash.")
        except Exception as e:
            print(f"Warning: Could not move '{screen_jpg}' to Trash: {e}", file=sys.stderr)

def process_file(input_file, threshold, padding):
    """
    Process a single input file: detect scenes, apply padding, split video, and handle auxiliary files.

    If no transition points are found, nothing is done and the file remains in its original location.

    :param input_file: Path to the input video file.
    :param threshold: Scene detection threshold.
    :param padding: Padding in seconds around each transition.
    """
    print(f"\nProcessing '{input_file}'...")

    # Detect scenes
    scenes = detect_scenes(input_file, threshold)
    if not scenes:
        print(f"No transition points were found in '{input_file}'. Doing nothing.")
        return
    print(f"Detected {len(scenes)} scene change(s).")

    # Get video duration
    video_duration = get_video_duration(input_file)
    print(f"Video duration: {video_duration:.3f} seconds.")

    # Define scene boundaries (each scene is a tuple of (start_time, end_time))
    scene_boundaries = get_scene_boundaries(scenes, video_duration)

    # Apply padding
    segments = apply_padding(scene_boundaries, padding, video_duration)
    print(f"Total segments after applying padding: {len(segments)}")

    # Prepare directories
    base_name, _ = os.path.splitext(os.path.basename(input_file))
    input_dir = os.path.dirname(os.path.abspath(input_file))
    transitions_dir = os.path.join(input_dir, "transitions")
    os.makedirs(transitions_dir, exist_ok=True)
    output_dir = os.path.join(transitions_dir, f"{base_name}_segments")
    os.makedirs(output_dir, exist_ok=True)

    # Split video
    if segments:
        split_video(input_file, segments, output_dir)
    else:
        print(f"No valid segments to create for '{input_file}'.", file=sys.stderr)

    # Move the original file into the transitions directory
    move_original(input_file, transitions_dir)

    # Move corresponding '-screen.jpg' to Trash if it exists
    move_screen_jpg(input_file)

def main():
    args = parse_arguments()

    input_files = args.input_files
    threshold = args.g
    padding = args.p

    # Validate threshold
    if threshold < 0.0 or threshold > 100.0:
        print(f"Error: Invalid threshold '{threshold}'. Must be between 0.0 and 100.0.", file=sys.stderr)
        sys.exit(1)

    # Process each input file
    for input_file in input_files:
        if not os.path.isfile(input_file):
            print(f"Error: File '{input_file}' not found. Skipping.", file=sys.stderr)
            continue
        process_file(input_file, threshold, padding)

    print("\nAll done!")

if __name__ == "__main__":
    main()
