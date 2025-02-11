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
    except:
        print("\nCouldn't verify admin privileges.")
        return False

class TXRMConfigConverter:
    def __init__(self):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.config = None  # Initialize as None
    
    def create_config_from_txrm(self, txrm_path):
        try:
            # Reset config object for each new file
            self.config = ConfigParser.ConfigParser()
            
            self.dataset.ReadFile(txrm_path)
            self._init_config_sections()
            self._fill_general_section()
            self._fill_geometry_section()
            self._fill_ct_section()
            self._fill_image_section()
            self._fill_detector_section()
            self._fill_xray_section()
            self._fill_axis_section()
            return True
        except Exception as e:
            print("Error processing TXRM file: {0}".format(str(e)))
            return False
    
    def _init_config_sections(self):
        sections = ['General', 'Geometry', 'CT', 'Image', 'Detector', 'Xray', 'Axis']
        for section in sections:
            self.config.add_section(section)
    
    def _fill_general_section(self):
        self.config.set('General', 'Version', '2.8.2.20099')
        self.config.set('General', 'Version-pca', '2')
        self.config.set('General', 'Comment', '')
        self.config.set('General', 'LoadDefault', '1')
        self.config.set('General', 'SystemName', 'ZEISS XRM')
    
    def _fill_geometry_section(self):
        idx = 0
        self.config.set('Geometry', 'FDD', str(self.dataset.GetDetectorToRADistance(idx)))
        self.config.set('Geometry', 'FOD', str(self.dataset.GetSourceToRADistance(idx)))
        self.config.set('Geometry', 'VoxelSizeX', str(self.dataset.GetPixelSize()))
        self.config.set('Geometry', 'VoxelSizeY', str(self.dataset.GetPixelSize()))
    
    def _fill_ct_section(self):
        num_projections = self.dataset.GetProjections()
        self.config.set('CT', 'NumberImages', str(num_projections))
        self.config.set('CT', 'Type', '0')
        self.config.set('CT', 'RotationSector', '360.00000000')
        self.config.set('CT', 'NrImgDone', str(num_projections))
    
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
    
    def _fill_xray_section(self):
        voltage = self.dataset.GetVoltage()  # in kV
        power = self.dataset.GetPower()      # in W
        
        # Calculate current (I = P/V) and convert to mA
        # Power is in W, voltage is in kV, so multiply by 1000 to get mA
        current = (power / voltage) * 1000 if voltage != 0 else 0
        
        self.config.set('Xray', 'Voltage', str(int(voltage)))
        self.config.set('Xray', 'Power', str(int(power)))
        self.config.set('Xray', 'Current', str(int(current)))
        self.config.set('Xray', 'Filter', str(self.dataset.GetFilter()))
    
    def _fill_axis_section(self):
        idx = 0
        axes = self.dataset.GetAxesNames()
        for axis in axes:
            pos = self.dataset.GetAxisPosition(idx, axis)
            clean_name = axis.replace(" ", "")
            self.config.set('Axis', clean_name, str(pos))
    
    def save_config(self, output_path):
        try:
            with open(output_path, 'w') as configfile:
                self.config.write(configfile)
            return True
        except Exception as e:
            print("Error saving config file: {0}".format(str(e)))
            return False

class EnhancedTXRMProcessor:
    def __init__(self, output_dir=None):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        self.all_metadata = []
        self.config_converter = TXRMConfigConverter()
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        log_file = os.path.join(self.output_dir, 
                               'processing_{0}.log'.format(
                                   datetime.now().strftime("%Y%m%d_%H%M%S")))
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def is_drift_file(self, file_path):
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
            for root, dirs, files in os.walk(search_path):
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

    def get_metadata(self, file_path):
        try:
            print("\nProcessing file: {0}".format(file_path))
            self.dataset.ReadFile(file_path)
            
            voltage = self.dataset.GetVoltage()  # in kV
            power = self.dataset.GetPower()      # in W
            current = (power / voltage) * 1000 if voltage != 0 else 0  # Calculate current in mA
            
            axes = self.dataset.GetAxesNames()
            num_projections = self.dataset.GetProjections()
            
            metadata = {
                "file_info": {
                    "file_path": file_path,
                    "file_hyperlink": '=HYPERLINK("{0}", "Click to Open")'.format(
                        file_path.replace("\\", "\\\\")),
                    "file_name": os.path.basename(file_path),
                    "folder_path": os.path.dirname(file_path),
                    "acquisition_complete": self.dataset.IsInitializedCorrectly()
                },
                "machine_settings": {
                    "objective": self.dataset.GetObjective(),
                    "pixel_size_um": self.dataset.GetPixelSize(),
                    "power_watts": power,
                    "voltage_kv": voltage,
                    "current_ma": current,
                    "filter": self.dataset.GetFilter(),
                    "binning": self.dataset.GetBinning()
                },
                "image_properties": {
                    "height_pixels": self.dataset.GetHeight(),
                    "width_pixels": self.dataset.GetWidth(),
                    "total_projections": num_projections
                },
                "projection_summary": self._get_projection_summary(num_projections, axes)
            }
            
            self.all_metadata.append(self._flatten_metadata(metadata))
            return metadata

        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return None
        finally:
            gc.collect()

    def _get_projection_summary(self, num_projections, axes):
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

    def _flatten_metadata(self, metadata):
        flat_data = {}
        
        # Collect all metadata as before
        flat_data['file_hyperlink'] = metadata['file_info']['file_hyperlink']
        
        for key, value in metadata['file_info'].items():
            if key != 'file_hyperlink':
                flat_data["file_{0}".format(key)] = value
            
        for key, value in metadata['machine_settings'].items():
            flat_data["machine_{0}".format(key)] = value
            
        for key, value in metadata['image_properties'].items():
            flat_data["image_{0}".format(key)] = value
            
        for key, value in metadata['projection_summary'].items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_data["proj_{0}_{1}".format(key, subkey)] = subvalue
            else:
                flat_data["proj_{0}".format(key)] = value
        
        # Define ordered fields
        ordered_fields = [
            'file_name',                    # file name of the .txrm
            'file_hyperlink',              # link to open the file
            'machine_voltage_kv',          # voltage
            'machine_current_ma',          # current
            'machine_power_watts',         # power
            'image_total_projections',     # number of projections
            'machine_pixel_size_um',       # pixel size
            'proj_time_span_end_date',     # project end date
            'proj_time_span_start_date',   # project start date
        ]
        
        # Create ordered dictionary with specified fields first
        ordered_data = {}
        
        # Add ordered fields first
        for field in ordered_fields:
            ordered_data[field] = flat_data.get(field, '')
        
        # Add remaining fields
        for key in flat_data:
            if key not in ordered_fields:
                ordered_data[key] = flat_data[key]
        
        return ordered_data

    def save_individual_csv(self, metadata, file_path):
        """Save a single row CSV file next to the TXRM file"""
        try:
            csv_path = os.path.splitext(file_path)[0] + '_metadata.csv'
            flat_metadata = self._flatten_metadata(metadata)
            
            # Use all fields from the flattened metadata
            fieldnames = flat_metadata.keys()
            
            with open(csv_path, 'wb') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(flat_metadata)
                
            print("Individual CSV saved to: {0}".format(csv_path))
            return True
            
        except Exception as e:
            error_msg = "Error saving individual CSV: {0}".format(str(e))
            print(error_msg)
            self.logger.error(error_msg)
            return False

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
            
            # Save individual CSV file
            self.save_individual_csv(metadata, file_path)
            
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

    def save_to_csv(self, filename="metadata_summary.csv"):
        if not self.all_metadata:
            print("No metadata to save")
            return

        output_path = os.path.join(self.output_dir, filename)
        
        try:
            # Collect all possible fieldnames from all metadata entries
            all_fieldnames = set()
            for metadata in self.all_metadata:
                all_fieldnames.update(metadata.keys())
            
            # Convert to list and ensure our preferred order
            ordered_fields = [
                'file_name',                    # file name of the .txrm
                'file_hyperlink',              # link to open the file
                'machine_voltage_kv',          # voltage
                'machine_current_ma',          # current
                'machine_power_watts',         # power
                'image_total_projections',     # number of projections
                'machine_pixel_size_um',       # pixel size
                'proj_time_span_end_date',     # project end date
                'proj_time_span_start_date',   # project start date
            ]
            
            # Create final fieldnames list with ordered fields first
            fieldnames = ordered_fields + [f for f in all_fieldnames if f not in ordered_fields]
            
            with open(output_path, 'wb') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                # Ensure all rows have all fields (with empty strings for missing fields)
                for row in self.all_metadata:
                    complete_row = {field: row.get(field, '') for field in fieldnames}
                    writer.writerow(complete_row)
            
            print("\nMetadata summary saved to: {0}".format(output_path))
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

    processor = EnhancedTXRMProcessor()
    
    search_path = raw_input("\nEnter folder path containing .txrm files: ").strip('"')
    while not os.path.exists(search_path):
        print("Path does not exist!")
        search_path = raw_input("Enter a valid folder path: ").strip('"')
    
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
    print("Check each .txrm location for config files")
    print("Check the 'metadata_output' folder for the CSV summary.")

if __name__ == "__main__":
    main()
