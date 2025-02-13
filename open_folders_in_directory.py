#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse

MAX_TABS = 10  # Maximum number of Finder tabs allowed

def get_subfolders_ordered(directory):
    """
    Get subfolders within the given directory up to two levels deep.
    Ensures that first-level subfolders are listed before second-level.
    """
    first_level = []
    second_level = []

    # Level 1: Immediate subfolders
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir():
                    first_level.append(entry.path)
    except PermissionError as e:
        print(f"Permission denied accessing {directory}: {e}")
        sys.exit(1)

    # Level 2: Subfolders within each immediate subfolder
    for subfolder in first_level.copy():  # Copy to avoid modification during iteration
        try:
            with os.scandir(subfolder) as entries:
                for entry in entries:
                    if entry.is_dir():
                        second_level.append(entry.path)
        except PermissionError as e:
            print(f"Permission denied accessing {subfolder}: {e}")
            # Continue with other subfolders

    # Combine first-level and second-level, ensuring first-level are first
    ordered_subfolders = first_level + second_level
    return ordered_subfolders

def construct_applescript(main_folder, subfolders, initial=True):
    """
    Construct an AppleScript that opens the main_folder and subfolders in Finder tabs.
    If initial is True, it creates a new Finder window. Otherwise, it adds tabs to the front window.
    """
    # Escape backslashes and quotes in paths
    def escape_path(path):
        return path.replace('\\', '\\\\').replace('"', '\\"')

    escaped_main_folder = escape_path(main_folder)

    if initial:
        # Start the AppleScript for initial opening
        script = f'''
        tell application "Finder"
            activate
            try
                set mainFolder to POSIX file "{escaped_main_folder}" as alias
                set theWindow to make new Finder window to mainFolder
                set current view of theWindow to list view
            on error
                display dialog "Cannot open the main folder: {escaped_main_folder}" buttons {{"OK"}} default button "OK"
                return
            end try
        '''
    else:
        # Start the AppleScript for adding new tabs to the front window
        script = '''
        tell application "Finder"
            activate
            try
                set theWindow to front Finder window
            on error
                display dialog "No Finder window is open to add new tabs." buttons {"OK"} default button "OK"
                return
            end try
        '''

    # Add each subfolder to be opened in a new tab
    for subfolder in subfolders:
        escaped_subfolder = escape_path(subfolder)
        script += f'''
            try
                delay 0.6 -- Allow Finder to process the previous command
                tell application "System Events"
                    keystroke "t" using {{command down}} -- Open a new tab
                end tell
                delay 0.6 -- Allow the new tab to be created
                set target of front Finder window to (POSIX file "{escaped_subfolder}" as alias)
            on error
                display dialog "Cannot open subfolder: {escaped_subfolder}" buttons {{"OK"}} default button "OK"
            end try
        '''

    # End the AppleScript
    script += '''
        end tell
        '''
    return script

def open_tabs_via_applescript(main_folder, subfolders, initial=True):
    """
    Executes the AppleScript to open the given subfolders in Finder.
    If initial is True, it creates a new window; otherwise, it adds tabs to the existing window.
    """
    applescript = construct_applescript(main_folder, subfolders, initial)

    # Execute the AppleScript using osascript
    try:
        process = subprocess.run(['osascript', '-e', applescript], check=True, text=True, capture_output=True)
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(process.stderr)
    except subprocess.CalledProcessError as e:
        print("An error occurred while executing AppleScript:")
        print(e.stderr)
        sys.exit(1)

def open_folders_in_finder(directory):
    """
    Opens the specified directory and its subfolders (up to two levels deep) in Finder tabs.
    Enforces a maximum of 10 tabs initially and prompts the user to open the rest.
    """
    # Validate the directory
    if not os.path.isdir(directory):
        print(f"Error: The path '{directory}' is not a valid directory.")
        sys.exit(1)

    # Get absolute path
    directory = os.path.abspath(directory)

    # Get ordered subfolders: first-level followed by second-level
    subfolders = get_subfolders_ordered(directory)

    # Calculate total tabs (main folder + subfolders)
    total_tabs = 1 + len(subfolders)  # 1 for the main folder

    # Determine how many tabs can be opened initially
    initial_tabs_allowed = MAX_TABS
    if total_tabs > MAX_TABS:
        initial_subfolders = subfolders[:MAX_TABS - 1]  # Main folder + first (MAX_TABS -1) subfolders
        remaining_subfolders = subfolders[MAX_TABS - 1:]
    else:
        initial_subfolders = subfolders
        remaining_subfolders = []

    # Open the initial batch of tabs
    open_tabs_via_applescript(directory, initial_subfolders, initial=True)

    # Notify the user if there are remaining tabs
    if remaining_subfolders:
        remaining_count = len(remaining_subfolders)
        print(f"There are {remaining_count} more tab(s) to open.")
        while True:
            user_input = input("Would you like to open the remaining tabs? (y/n): ").strip().lower()
            if user_input in ['y', 'yes']:
                open_tabs_via_applescript(directory, remaining_subfolders, initial=False)
                print("Remaining tabs have been opened.")
                break
            elif user_input in ['n', 'no']:
                print("Remaining tabs were not opened.")
                break
            else:
                print("Please enter 'y' or 'n'.")

def main():
    parser = argparse.ArgumentParser(description='Open a directory and its subfolders (up to two levels deep) in Finder tabs with a maximum of 10 tabs initially.')
    parser.add_argument('directory', metavar='DIRECTORY', type=str, help='Path to the directory to open.')
    args = parser.parse_args()

    open_folders_in_finder(args.directory)

if __name__ == '__main__':
    main()
