# -*- coding: utf-8 -*-
from __future__ import print_function, division  # Add division for Python 2.7
import os
import ctypes
from utils.file_utils import find_txrm_files, get_user_input
from utils.progress_tracker import ProgressTracker
from config.user_config import UserConfig
from processors.txrm_processor import TXRMProcessor

def check_admin():
    """Cross-platform admin check"""
    try:
        if os.name == 'nt':  # Windows
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:  # Unix-based systems
            return os.geteuid() == 0
    except Exception as e:
        print("\nCouldn't verify admin privileges: {0}".format(str(e)))
        return False

def _handle_interactive_mode(file_path):
    process_file = get_user_input(
        "Process this file? (y/n/q to quit): ",
        ['y', 'n', 'q']
    )
    
    if process_file == 'q':
        print("\nProcessing stopped by user.")
        return False
    elif process_file == 'n':
        return True
    return True

def main():
    if not check_admin():
        user_input = get_user_input("Continue anyway? (y/n): ", ['y', 'n'])
        if user_input != 'y':
            print("Exiting...")
            return

    # Setup configuration
    config = UserConfig()
    config.setup_from_user_input()
    
    # Initialize processor
    processor = TXRMProcessor(
        output_dir=os.path.join(config.output_dir, "metadata_output")
    )
    
    # Find files
    txrm_files = find_txrm_files(config.search_path, config.include_drift)
    if not txrm_files:
        print("\nNo .txrm files found in the specified path.")
        return
    
    # Initialize progress tracker
    progress = ProgressTracker(len(txrm_files))
    
    # Process files
    for i, file_path in enumerate(txrm_files, 1):
        print("\nFile {0} of {1}:".format(i, len(txrm_files)))
        print(file_path)
        
        if config.process_mode == '2':
            if not _handle_interactive_mode(file_path):
                break
        
        success = processor.process_single_file(file_path)
        progress.update(file_path, success)
        
        # Show progress
        prog_info = progress.get_progress()
        print("\nProgress: {0:.1f}% ({1}/{2} files)".format(
            prog_info['percentage'],
            prog_info['processed'],
            prog_info['total']
        ))
    
    # Save cumulative CSV
    if processor.all_metadata:
        processor.save_cumulative_csv()
    
    print("\nProcessing complete!")
    print("Check each .txrm location for metadata text and config files")
    print("Check the 'metadata_output' folder for the cumulative CSV file.")

if __name__ == "__main__":
    main() 