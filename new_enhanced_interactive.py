# -*- coding: utf-8 -*-
from __future__ import print_function  # Import print function for compatibility
import os
import sys
import json
import csv
import ctypes
import ConfigParser
from XradiaPy import Data
from datetime import datetime
import logging
import gc

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
    
    def _fill_image_section(self):
        width = self.dataset.GetWidth()
        height = self.dataset.GetHeight()
        self.config.set('Image', 'DimX', str(width))
        self.config.set('Image', 'DimY', str(height))
        self.config.set('Image', 'Top', '0')
        self.config.set('Image', 'Left', '0')
        self.config.set('Image', 'Bottom', str(height-1))
        self.config.set('Image', 'Right', str(width-1))
    
    def _fill_detector_section(self):
        idx = 0
        self.config.set('Detector', 'Binning', str(self.dataset.GetBinning()))
        self.config.set('Detector', 'BitPP', '16')
        self.config.set('Detector', 'TimingVal', str(self.dataset.GetExposure(idx)))
        self.config.set('Detector', 'NrPixelsX', str(self.dataset.GetWidth()))
        self.config.set('Detector', 'NrPixelsY', str(self.dataset.GetHeight()))
    
    def _fill_axis_section(self):
        idx = 0
        axes = self.dataset.GetAxesNames()
        for axis in axes:
            pos = self.dataset.GetAxisPosition(idx, axis)
            clean_name = axis.replace(" ", "")
            self.config.set('Axis', clean_name, str(pos))
    
    def _fill_general_section(self):
        self.config.set('General', 'Version', '2.8.2.20099')
        self.config.set('General', 'Version-pca', '2')
        self.config.set('General', 'Comment', '')
        self.config.set('General', 'LoadDefault', '1')
        self.config.set('General', 'SystemName', 'ZEISS XRM')
    
    def save_config(self, output_path):
        try:
            # Save with sections in the desired order (Xray removed)
            with open(output_path, 'w') as configfile:
                for section in ['Geometry', 'CT', 'Image', 'Detector', 'Axis', 'General']:
                    self.write_section(section, configfile)
            return True
        except Exception as e:
            print("Error saving config file: {0}".format(str(e)))
            return False

    def write_section(self, section, configfile):
        """Helper method to write a section in the desired format"""
        configfile.write('[{0}]\n'.format(section))
        for option in self.config.options(section):
            value = self.config.get(section, option)
            configfile.write('{0} = {1}\n'.format(option, value))
        configfile.write('\n')

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

    def find_txrm_files(self, search_path, include_drift=False):
        txrm_files = []
        folder_structure = {}
        total_files = 0
        drift_files = 0
        
        print("\nSearching for .txrm files in: {0}".format(search_path))
        
        try:
            for root, _, files in os.walk(search_path):
                txrm_in_folder = [f for f in files if f.lower().endswith('.txrm')]
                if txrm_in_folder:
                    # Filter out drift files if not included
                    if not include_drift:
                        txrm_in_folder = [f for f in txrm_in_folder if not self.is_drift_file(f)]
                    
                    rel_path = os.path.relpath(root, search_path)
                    folder_structure[rel_path] = len(txrm_in_folder)
                    total_files += len(txrm_in_folder)
                    
                    for file in txrm_in_folder:
                        full_path = os.path.join(root, file)
                        txrm_files.append(full_path)
                        if self.is_drift_file(file):
                            drift_files += 1
                        print("Found: {0}".format(full_path))

            print("\nFolder Structure Summary:")
            for folder, count in folder_structure.items():
                print("  {0}: {1} TXRM files".format(folder, count))
            print("\nTotal TXRM files found: {0}".format(total_files))
            if drift_files > 0:
                print("Drift files {0}: {1}".format(
                    "included" if include_drift else "excluded",
                    drift_files
                ))
        
        except Exception as e:
            error_msg = "Directory search error: {0}".format(str(e))
            print(error_msg)
            self.logger.error(error_msg)
        
        return txrm_files

    def _calculate_scan_time(self, start_time, end_time):
        """Calculate and format scan time"""
        if not (start_time and end_time):
            return ''
        
        time_diff = end_time - start_time
        
        # Convert to hours, minutes, seconds
        total_seconds = int(time_diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

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

            # Calculate scan time if timestamps available
            if 'projection_summary' in metadata:
                start_time = metadata['projection_summary']['time_span']['start_date']
                end_time = metadata['projection_summary']['time_span']['end_date']
                metadata['projection_summary']['scan_time'] = self._calculate_scan_time(start_time, end_time)

            self.all_metadata.append(self._flatten_metadata(metadata))
            return metadata

        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return None
        finally:
            gc.collect()

    @staticmethod
    def _get_projection_summary(num_projections, axes):
        if num_projections == 0:
            return {}

        try:
            summary = {
                "projection_count": num_projections,
                "time_span": {
                    "start_date": self.dataset.GetDate(0),
                    "end_date": self.dataset.GetDate(num_projections - 1)
                },
                "exposure": self.dataset.GetExposure(0)
            }

            for axis in axes:
                first_pos = self.dataset.GetAxisPosition(0, axis)
                last_pos = self.dataset.GetAxisPosition(num_projections - 1, axis)
                summary["{0}_start".format(axis)] = first_pos
                summary["{0}_end".format(axis)] = last_pos
                summary["{0}_range".format(axis)] = last_pos - first_pos

            return summary

        except Exception as e:
            print("Error creating projection summary: {0}".format(str(e)))
            return {}

    EXPECTED_COLUMNS = [
        'FILE NAME',                                    # minus .txrm
        'File hyperlink',                              # clickable link
        'CT: Voxel size (um)',                         # from machine_pixel_size_um
        'CT: Objective',                               # from machine_objective
        'CT: Number of images',                        # from image_total_projections
        'CT: Optical magnification',                   # if 4x,20x,40x then yes else no
        'X-ray Tube: voltage',                         # from machine_voltage_kv
        'X-ray Tube: power (W)',                       # from machine_power_watts
        'Xray tube: current (uA)',                     # (power_watts/voltage_kv)*100
        'X-ray: Filter',                               # from machine_filter
        'Detector: Binning',                           # from machine_binning
        'Detector: capture time (s)',                  # from proj_exposure
        'Detector: Averaging',                         # from proj_projection_count
        'Image width (pixels)',                        # from image_width_pixels
        'Image height (pixels)',                       # from image_height_pixels
        'Image width real',                            # width_pixels * pixel_size_um
        'Image height real',                           # height_pixels * pixel_size_um
        'Scan time',                                   # end_date - start_date
        'Start time',                                  # from proj_time_span_end_date
        'End time',                                    # from proj_time_span_start_date
        'TXRM File path',                              # from file_file_path
        'File path',                                   # from file_folder_path
        'Acquisition stage successful?',               # from file_acquisition_complete
        'Sample: X-axis start position',               # from proj_Sample X_start
        'Sample: X-axis end position',                 # from proj_Sample X_end
        'Sample: X-axis range',                        # from proj_Sample X_range
        'Sample: Y-axis start position',               # from proj_Sample Y_start
        'Sample: Y-axis end position',                 # from proj_Sample Y_end
        'Sample: Y-axis range',                        # from proj_Sample Y_range
        'Sample: Z-axis start position',               # from proj_Sample Z_start
        'Sample: Z-axis end position',                 # from proj_Sample Z_end
        'Sample: Z-axis range (um)',                   # from proj_Sample Z_range
        'Sample: rotation start position',             # from proj_Sample Theta_start
        'Sample: rotation end position',               # from proj_Sample Theta_end
        'Sample: rotation range',                      # from proj_Sample Theta_range
        'Source: X-axis start position',               # from proj_Source X_start
        'Source: Z-axis start position',               # from proj_Source Z_start
        'Source: Z-axis end position',                 # from proj_Source Z_end
        'Source: X-axis end position',                 # from proj_Source X_end
        'Source: Z-axis range',                        # from proj_Source Z_range
        'Detector: Flat panel Z-axis start position',  # from proj_Flat Panel Z_start
        'Detector: Flat panel Z-axis end position',    # from proj_Flat Panel Z_end
        'Detector: flat panel range',                  # from proj_Flat Panel Z_range
        'Detector: Flat panel X-axis start position',  # from proj_Flat Panel X_start
        'Detector: Flat panel X-axis end position',    # from proj_Flat Panel X_end
        'Sample: Flat panel X-axis range',             # from proj_Flat Panel X_range
        'Detector: Z-axis start position',             # from proj_Detector Z_start
        'Detector: Z-axis end position',               # from proj_Detector Z_end
        '???: Z-axis start position',                  # from proj_CCD_Z_start
        '???: X-axis start position',                  # from proj_CCD_X_start
        '???: Z-axis end position',                    # from proj_CCD_Z_end
        '???: Final X-axis position',                  # from proj_CCD_X_end
        '???: X-axis range',                           # from proj_CCD_X_range
        '???: Z-axis range'                            # from proj_CCD_Z_range
    ]

    def _flatten_metadata(self, metadata):
        # Create a dictionary with all possible fields initialized to empty string
        flat_data = {col: '' for col in self.EXPECTED_COLUMNS}
        
        # Get base filename without extension
        file_path = metadata['file_info']['file_path']
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Map the metadata to the expected column names
        flat_data.update({
            'FILE NAME': base_filename,
            'File hyperlink': '=HYPERLINK("{0}", "Click to Open")'.format(file_path.replace("\\", "\\\\")),
            'CT: Voxel size (um)': metadata['machine_settings']['pixel_size_um'],
            'CT: Objective': metadata['machine_settings']['objective'],
            'CT: Number of images': metadata['image_properties']['total_projections'],
            'CT: Optical magnification': 'yes' if any(x in str(metadata['machine_settings'].get('objective', '')).lower() 
                                                        for x in ['4x', '20x', '40x']) else 'no',
            'X-ray Tube: voltage': metadata['machine_settings']['voltage_kv'],
            'X-ray Tube: power (W)': metadata['machine_settings']['power_watts'],
            'Xray tube: current (uA)': (metadata['machine_settings']['power_watts'] / 
                                          metadata['machine_settings']['voltage_kv'] * 100  
                                          if metadata['machine_settings']['voltage_kv'] != 0 else 0),
            'X-ray: Filter': metadata['machine_settings']['filter'],
            'Detector: Binning': metadata['machine_settings']['binning'],
            'Detector: capture time (s)': metadata['projection_summary'].get('exposure', ''),
            'Detector: Averaging': metadata['projection_summary'].get('projection_count', ''),
            'Image width (pixels)': metadata['image_properties']['width_pixels'],
            'Image height (pixels)': metadata['image_properties']['height_pixels'],
            'Image width real': metadata['image_properties']['width_real'],
            'Image height real': metadata['image_properties']['height_real'],
            'Scan time': metadata['projection_summary'].get('scan_time', ''),
            'Start time': metadata['projection_summary']['time_span']['start_date'].strftime('%Y-%m-%d %H:%M:%S') 
                         if metadata['projection_summary']['time_span']['start_date'] else '',
            'End time': metadata['projection_summary']['time_span']['end_date'].strftime('%Y-%m-%d %H:%M:%S') 
                       if metadata['projection_summary']['time_span']['end_date'] else '',
            'TXRM File path': metadata['file_info']['file_path'],
            'File path': metadata['file_info']['folder_path'],
            'Acquisition stage successful?': metadata['file_info']['acquisition_complete']
        })

        # Map axis positions to the expected column names
        axis_mapping = {
            'Sample_X': 'Sample: X-axis',
            'Sample_Y': 'Sample: Y-axis',
            'Sample_Z': 'Sample: Z-axis',
            'Sample_Theta': 'Sample: rotation',
            'Source_X': 'Source: X-axis',
            'Source_Z': 'Source: Z-axis',
            'Flat_Panel_Z': 'Detector: Flat panel Z-axis',
            'Flat_Panel_X': 'Detector: Flat panel X-axis'
        }

        for orig_name, column_prefix in axis_mapping.items():
            for suffix, column_suffix in [('start', 'start position'), 
                                            ('end', 'end position'), 
                                            ('range', 'range')]:
                proj_key = 'proj_{}_{}'.format(orig_name, suffix)
                if proj_key in metadata['projection_summary']:
                    column_name = '{} {}'.format(column_prefix, column_suffix)
                    flat_data[column_name] = metadata['projection_summary'][proj_key]

        return flat_data

    def process_single_file(self, file_path):
        try:
            print("\nProcessing: {0}".format(file_path))
            
            # Get metadata
            metadata = self.get_metadata(file_path)
            if not metadata:
                return None
            
            # Generate config file
            config_path = os.path.splitext(file_path)[0] + "_config.txt"
            if self.config_converter.create_config_from_txrm(file_path):
                if self.config_converter.save_config(config_path):
                    print("Configuration saved to: {0}".format(config_path))
                else:
                    print("Failed to save configuration file!")
            else:
                print("Failed to create configuration!")
            
            # Create individual log file
            log_filename = os.path.splitext(os.path.basename(file_path))[0] + '_processing.log'
            log_path = os.path.join(os.path.dirname(file_path), log_filename)
            
            # Create a file handler for this specific log
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
            
            # Log processing information
            self.logger.info("Processing completed for: %s", file_path)
            self.logger.info("Metadata extracted successfully")
            self.logger.info("Configuration file saved to: %s", config_path)
            
            # Remove the file handler
            self.logger.removeHandler(file_handler)
            file_handler.close()
            
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
