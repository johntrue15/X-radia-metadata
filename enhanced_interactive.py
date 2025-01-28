import os
import sys
import json
import csv
import ctypes
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

class EnhancedTXRMProcessor:
    def __init__(self, output_dir=None):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        self.all_metadata = []  # Store metadata from all files
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Setup logging
        log_file = os.path.join(self.output_dir, 
                               'processing_{0}.log'.format(
                                   datetime.now().strftime("%Y%m%d_%H%M%S")))
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def find_txrm_files(self, search_path):
        """Find all .txrm files in given path and subfolders"""
        txrm_files = []
        folder_structure = {}
        total_files = 0
        
        print("\nSearching for .txrm files in: {0}".format(search_path))
        
        try:
            for root, dirs, files in os.walk(search_path):
                txrm_in_folder = [f for f in files if f.lower().endswith('.txrm')]
                if txrm_in_folder:
                    rel_path = os.path.relpath(root, search_path)
                    folder_structure[rel_path] = len(txrm_in_folder)
                    total_files += len(txrm_in_folder)
                    
                    for file in txrm_in_folder:
                        full_path = os.path.join(root, file)
                        txrm_files.append(full_path)
                        print("Found: {0}".format(full_path))

            print("\nFolder Structure Summary:")
            for folder, count in folder_structure.items():
                print("  {0}: {1} TXRM files".format(folder, count))
            print("\nTotal TXRM files found: {0}".format(total_files))
        
        except Exception as e:
            error_msg = "Directory search error: {0}".format(str(e))
            print(error_msg)
            self.logger.error(error_msg)
        
        return txrm_files

    def get_metadata(self, file_path):
        """Extract metadata from a single file"""
        try:
            print("\nProcessing file: {0}".format(file_path))
            self.dataset.ReadFile(file_path)
            
            # Get all available axes
            axes = self.dataset.GetAxesNames()
            
            # Get number of projections
            num_projections = self.dataset.GetProjections()
            
            metadata = {
                "file_info": {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "folder_path": os.path.dirname(file_path),
                    "acquisition_complete": self.dataset.IsInitializedCorrectly()
                },
                
                "machine_settings": {
                    "objective": self.dataset.GetObjective(),
                    "pixel_size_um": self.dataset.GetPixelSize(),
                    "power_watts": self.dataset.GetPower(),
                    "voltage_kv": self.dataset.GetVoltage(),
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
            
            # Add to collection of all metadata
            self.all_metadata.append(self._flatten_metadata(metadata))
            
            return metadata

        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return None
        finally:
            gc.collect()  # Force garbage collection

    def _get_projection_summary(self, num_projections, axes):
        """Create summary of projection data"""
        if num_projections == 0:
            return {}

        try:
            # Get data from first and last projections
            summary = {
                "projection_count": num_projections,
                "time_span": {
                    "start_date": self.dataset.GetDate(0),
                    "end_date": self.dataset.GetDate(num_projections - 1)
                },
                "exposure": self.dataset.GetExposure(0)
            }

            # Add axis positions
            for axis in axes:
                first_pos = self.dataset.GetAxisPosition(0, axis)
                last_pos = self.dataset.GetAxisPosition(num_projections - 1, axis)
                summary[f"{axis}_start"] = first_pos
                summary[f"{axis}_end"] = last_pos
                summary[f"{axis}_range"] = last_pos - first_pos

            return summary

        except Exception as e:
            print("Error creating projection summary: {0}".format(str(e)))
            return {}

    def _flatten_metadata(self, metadata):
        """Flatten nested metadata structure for CSV export"""
        flat_data = {}
        
        # File info
        for key, value in metadata['file_info'].items():
            flat_data[f"file_{key}"] = value
            
        # Machine settings
        for key, value in metadata['machine_settings'].items():
            flat_data[f"machine_{key}"] = value
            
        # Image properties
        for key, value in metadata['image_properties'].items():
            flat_data[f"image_{key}"] = value
            
        # Projection summary
        for key, value in metadata['projection_summary'].items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_data[f"proj_{key}_{subkey}"] = subvalue
            else:
                flat_data[f"proj_{key}"] = value
                
        return flat_data

    def save_to_csv(self, filename="metadata_summary.csv"):
        """Save all metadata to a single CSV file"""
        if not self.all_metadata:
            print("No metadata to save")
            return

        output_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(output_path, 'wb') as csvfile:
                # Get fieldnames from first entry
                fieldnames = self.all_metadata[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(self.all_metadata)
                
            print("\nMetadata summary saved to: {0}".format(output_path))
            return output_path
            
        except Exception as e:
            error_msg = "Error saving CSV: {0}".format(str(e))
            print(error_msg)
            self.logger.error(error_msg)
            return None

def main():
    # Check for admin privileges
    if not check_admin():
        user_input = raw_input("Continue anyway? (y/n): ")
        if user_input.lower() != 'y':
            print("Exiting...")
            return

    processor = EnhancedTXRMProcessor()
    
    # Get search path
    search_path = raw_input("\nEnter folder path containing .txrm files: ").strip('"')
    while not os.path.exists(search_path):
        print("Path does not exist!")
        search_path = raw_input("Enter a valid folder path: ").strip('"')
    
    # Find files
    txrm_files = processor.find_txrm_files(search_path)
    
    if not txrm_files:
        print("\nNo .txrm files found in the specified path.")
        return
    
    # Process files
    for i, file_path in enumerate(txrm_files, 1):
        print("\nProcessing file {0} of {1}:".format(i, len(txrm_files)))
        processor.get_metadata(file_path)
    
    # Save summary CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = "metadata_summary_{0}.csv".format(timestamp)
    processor.save_to_csv(csv_filename)
    
    print("\nProcessing complete!")
    print("Check the 'metadata_output' folder for results.")

if __name__ == "__main__":
    main()
