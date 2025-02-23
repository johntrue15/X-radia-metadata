import os
import csv
from datetime import datetime
import gc
from ..config.txrm_config_converter import TXRMConfigConverter
from ..metadata.metadata_extractor import MetadataExtractor
from ..utils.logging_utils import setup_logger

class TXRMProcessor(object):
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        self.all_metadata = []
        self.config_converter = TXRMConfigConverter()
        self.metadata_extractor = MetadataExtractor()
        self.logger = setup_logger(self.output_dir)

    def process_single_file(self, file_path):
        try:
            print("\nProcessing: {}".format(file_path))
            
            # Get metadata
            metadata = self.metadata_extractor.get_complete_metadata(file_path)
            if not metadata:
                return None
            
            # Save metadata to CSV
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            self.save_to_csv(metadata, base_filename)
            
            # Generate config file
            config_path = os.path.splitext(file_path)[0] + "_config.txt"
            if self.config_converter.create_config_from_txrm(file_path):
                if self.config_converter.save_config(config_path):
                    print("Configuration saved to: {}".format(config_path))
                else:
                    print("Failed to save configuration file!")
            else:
                print("Failed to create configuration!")
            
            return metadata
            
        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return None
        finally:
            gc.collect()

    def save_to_csv(self, data, base_filename):
        # ... (CSV saving logic remains the same) 