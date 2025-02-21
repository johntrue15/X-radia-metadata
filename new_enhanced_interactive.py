# -*- coding: utf-8 -*-
from __future__ import print_function  # Import print function for compatibility
import os
import csv
import ctypes
import ConfigParser
import logging
import gc
from datetime import datetime
from XradiaPy import Data

def check_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("\nWARNING: Script requires administrator privileges.")
            print("Please run PyCharm as administrator.\n")
            return False
        return True
    except Exception as e:  # Catch specific exceptions
        print("\nCouldn't verify admin privileges: {}".format(str(e)))
        return False

class TXRMConfigConverter(object):
    def __init__(self):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.config = None  # Initialize as None
    
    def create_config_from_txrm(self, txrm_path):
        try:
            # Reset config object for each new file
            self.config = ConfigParser.ConfigParser()
            
            self.dataset.ReadFile(txrm_path)
            self._init_config_sections()
            self._fill_geometry_section()
            self._fill_ct_and_xray_section()  # Combined CT and Xray
            self._fill_image_section()
            self._fill_detector_section()
            self._fill_axis_section()
            self._fill_general_section()
            return True
        except Exception as e:
            print("Error processing TXRM file: {0}".format(str(e)))
            return False
    
    def _init_config_sections(self):
        # Remove Xray from sections list
        sections = ['Geometry', 'CT', 'Image', 'Detector', 'Axis', 'General']
        for section in sections:
            self.config.add_section(section)
    
    def _fill_geometry_section(self):
        idx = 0
        self.config.set('Geometry', 'FDD', str(self.dataset.GetDetectorToRADistance(idx)))
        self.config.set('Geometry', 'FOD', str(self.dataset.GetSourceToRADistance(idx)))
        self.config.set('Geometry', 'VoxelSizeX', str(self.dataset.GetPixelSize()))
        self.config.set('Geometry', 'VoxelSizeY', str(self.dataset.GetPixelSize()))
    
    def _fill_ct_and_xray_section(self):
        # CT data
        num_projections = self.dataset.GetProjections()
        self.config.set('CT', 'NumberImages', str(num_projections))
        self.config.set('CT', 'Type', '0')
        self.config.set('CT', 'RotationSector', '360.00000000')
        self.config.set('CT', 'NrImgDone', str(num_projections))
        
        # Add Xray data to CT section
        voltage = self.dataset.GetVoltage()  # in kV
        power = self.dataset.GetPower()      # in W
        current = (power / voltage) * 100 if voltage != 0 else 0  # Calculate current in µA
        
        self.config.set('CT', 'Voltage', str(int(voltage)))
        self.config.set('CT', 'Power', str(int(power)))
        self.config.set('CT', 'Current', str(int(current)))
        self.config.set('CT', 'Filter', str(self.dataset.GetFilter()))

class EnhancedTXRMProcessor(object):
    def __init__(self, output_dir=None):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        self.all_metadata = []
        self.config_converter = TXRMConfigConverter()
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        log_file = os.path.join(
            self.output_dir,
            'processing_{0}.log'.format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        )
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,  # Set to DEBUG to capture all logs
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def is_drift_file(file_path):
        """Check if file is a drift file based on name"""
        filename = os.path.basename(file_path).lower()
        return 'drift' in filename

    def get_metadata(self, file_path):
        try:
            self.logger.debug("Starting to process file: {}".format(file_path))  # Debug log
            print("\nProcessing file: {0}".format(file_path))
            self.dataset.ReadFile(file_path)
            
            # Basic file info
            metadata = {
                'file_info': {
                    'file_path': file_path,
                    'file_name': self.dataset.GetName(),
                    'folder_path': os.path.dirname(file_path),
                    'acquisition_complete': self.dataset.IsInitializedCorrectly()
                },
                'machine_settings': {
                    'objective': self.dataset.GetObjective(),
                    'pixel_size_um': self.dataset.GetPixelSize(),
                    'power_watts': self.dataset.GetPower(),
                    'voltage_kv': self.dataset.GetVoltage(),
                    'filter': self.dataset.GetFilter(),
                    'binning': self.dataset.GetBinning()
                },
                'image_properties': {
                    'height_pixels': self.dataset.GetHeight(),
                    'width_pixels': self.dataset.GetWidth(),
                    'total_projections': self.dataset.GetProjections()
                }
            }

            self.logger.debug("Metadata after initial setup: {}".format(metadata))  # Debug log

            # Get projection data
            num_projections = metadata['image_properties']['total_projections']
            self.logger.debug("Number of projections: {}".format(num_projections))  # Debug log

            if num_projections > 0:
                # Get first and last projection data
                first_proj = {
                    'time_span': {
                        'start_date': self.dataset.GetDate(0),
                        'end_date': self.dataset.GetDate(num_projections - 1)
                    },
                    'exposure': self.dataset.GetExposure(0),
                    'detector_to_ra_distance': self.dataset.GetDetectorToRADistance(0),
                    'source_to_ra_distance': self.dataset.GetSourceToRADistance(0)
                }

                self.logger.debug("First projection data: {}".format(first_proj))  # Debug log

                # Convert start_date and end_date to datetime objects
                start_date_str = first_proj['time_span']['start_date']
                end_date_str = first_proj['time_span']['end_date']

                # Assuming the date format is known, e.g., '%Y-%m-%d %H:%M:%S'
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S') if start_date_str else None
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S') if end_date_str else None

                # Calculate scan time if both dates are valid
                if start_date and end_date:
                    scan_time = end_date - start_date
                    first_proj['scan_time'] = str(scan_time)  # Store scan time as a string if needed

                # Get axis positions
                axes = self.dataset.GetAxesNames()
                for axis in axes:
                    first_pos = self.dataset.GetAxisPosition(0, axis)
                    last_pos = self.dataset.GetAxisPosition(num_projections - 1, axis)
                    clean_name = axis.replace(" ", "_")
                    first_proj[clean_name + "_start"] = first_pos
                    first_proj[clean_name + "_end"] = last_pos
                    first_proj[clean_name + "_range"] = last_pos - first_pos

                metadata['projection_summary'] = first_proj
                self.logger.debug("Projection summary: {}".format(metadata['projection_summary']))  # Debug log

            # Calculate derived values
            if metadata['machine_settings']['voltage_kv'] != 0:
                current_ua = (metadata['machine_settings']['power_watts'] / 
                             metadata['machine_settings']['voltage_kv']) * 100 if metadata['machine_settings']['voltage_kv'] != 0 else 0
                metadata['machine_settings']['current_ua'] = current_ua

            # Calculate real dimensions
            pixel_size = metadata['machine_settings']['pixel_size_um']
            metadata['image_properties']['width_real'] = (
                metadata['image_properties']['width_pixels'] * pixel_size)
            metadata['image_properties']['height_real'] = (
                metadata['image_properties']['height_pixels'] * pixel_size)

            self.all_metadata.append(self._flatten_metadata(metadata))
            return metadata

        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return None
        finally:
            gc.collect()

    def verify_columns(self, csv_path):
        """Verify that all expected columns are present and in correct order"""
        try:
            with open(csv_path, 'rb') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader)
                
                # Check if all columns are present
                missing = set(self.EXPECTED_COLUMNS) - set(header)
                extra = set(header) - set(self.EXPECTED_COLUMNS)
                
                # Check order
                order_correct = header == self.EXPECTED_COLUMNS
                
                print("\nColumn Verification Results:")
                if missing:
                    print("Missing columns:", missing)
                if extra:
                    print("Extra columns:", extra)
                if not order_correct:
                    print("Column order does not match expected order")
                    for i, (exp, got) in enumerate(zip(self.EXPECTED_COLUMNS, header)):
                        print("Position {}: Expected '{}', Got '{}'".format(i, exp, got))
                
                if not missing and not extra and order_correct:
                    print("✓ All columns present and in correct order")
                    return True
                return False
                
        except Exception as e:
            print("Error verifying columns: {}".format(str(e)))
            return False

    def save_to_csv(self, filename="metadata_summary.csv"):
        if not self.all_metadata:
            print("No metadata to save")
            return None

        output_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(output_path, 'wb') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.EXPECTED_COLUMNS)
                writer.writeheader()
                for row in self.all_metadata:
                    writer.writerow(row)
            
            print("\nMetadata summary saved to: {0}".format(output_path))
            
            # Verify columns after saving
            self.verify_columns(output_path)
            
            return output_path
            
        except Exception as e:
            error_msg = "Error saving CSV: {0}".format(str(e))
            print(error_msg)
            self.logger.error(error_msg)
            return None

def get_user_input(prompt, valid_responses=None):
    """Get user input with validation"""
    while True:
        response = raw_input(prompt).strip().lower()
        if valid_responses is None or response in valid_responses:
            return response
        print("Invalid input. Please try again.")

def main():
    if not check_admin():
        user_input = get_user_input("Continue anyway? (y/n): ", ['y', 'n'])
        if user_input != 'y':
            print("Exiting...")
            return

    search_path = raw_input("\nEnter folder path containing .txrm files: ").strip('"')
    while not os.path.exists(search_path):
        print("Path does not exist!")
        search_path = raw_input("Enter a valid folder path: ").strip('"')
    
    # Ask user where to save metadata output
    save_location = get_user_input(
        "\nWhere would you like to save the metadata output folder?\n"
        "1. Current working directory\n"
        "2. Same directory as TXRM files\n"
        "Enter (1/2): ",
        ['1', '2']
    )
    
    # Set output directory based on user choice
    output_dir = os.getcwd() if save_location == '1' else search_path
    processor = EnhancedTXRMProcessor(output_dir=os.path.join(output_dir, "metadata_output"))
    
    # Ask about processing drift files
    include_drift = get_user_input(
        "\nInclude drift files in processing? (y/n): ",
        ['y', 'n']
    ) == 'y'
    
    txrm_files = processor.find_txrm_files(search_path, include_drift)
    
    if not txrm_files:
        print("\nNo .txrm files found in the specified path.")
        return
    
    process_mode = get_user_input(
        "\nChoose processing mode:\n1. Process all files (batch)\n2. Confirm each file\nEnter (1/2): ",
        ['1', '2']
    )
    
    for i, file_path in enumerate(txrm_files, 1):
        print("\nFile {0} of {1}:".format(i, len(txrm_files)))
        print(file_path)
        
        if process_mode == '2':
            process_file = get_user_input(
                "Process this file? (y/n/q to quit): ",
                ['y', 'n', 'q']
            )
            
            if process_file == 'q':
                print("\nProcessing stopped by user.")
                break
            elif process_file == 'n':
                continue
        
        processor.process_single_file(file_path)
        
        if process_mode == '2':
            continue_proc = get_user_input(
                "\nContinue to next file? (y/n): ",
                ['y', 'n']
            )
            if continue_proc == 'n':
                print("\nProcessing stopped by user.")
                break
    
    # Save final CSV
    if processor.all_metadata:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = "metadata_summary_{0}.csv".format(timestamp)
        processor.save_to_csv(csv_filename)
    
    print("\nProcessing complete!")
    print("Check the 'metadata_output' folder for the CSV summary.")
    print("Check each .txrm location for config files")

if __name__ == "__main__":
    main()
