# -*- coding: utf-8 -*-
from __future__ import print_function, division
import os
import csv
from datetime import datetime
import gc

# Use absolute imports
from new_enhanced_interactive.config.txrm_config_converter import TXRMConfigConverter
from new_enhanced_interactive.metadata.metadata_extractor import MetadataExtractor
from new_enhanced_interactive.utils.logging_utils import setup_logger

class TXRMProcessor(object):
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        self.all_metadata = []  # Store metadata from all processed files
        self.config_converter = TXRMConfigConverter()
        self.metadata_extractor = MetadataExtractor()
        self.logger = setup_logger(self.output_dir)

    def save_metadata_txt(self, metadata, file_path):
        """Save metadata as formatted text file next to TXRM file"""
        txt_path = os.path.splitext(file_path)[0] + "_metadata.txt"
        try:
            with open(txt_path, 'w') as f:
                # Write file info
                f.write("TXRM File Metadata\n")
                f.write("=" * 50 + "\n\n")
                
                # Basic Info
                f.write("Basic Information:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['basic_info'].items():
                    f.write("{0}: {1}\n".format(key, value))
                f.write("\n")
                
                # Machine Settings
                f.write("Machine Settings:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['machine_settings'].items():
                    f.write("{0}: {1}\n".format(key, value))
                f.write("\n")
                
                # Image Properties
                f.write("Image Properties:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['image_properties'].items():
                    f.write("{0}: {1}\n".format(key, value))
                f.write("\n")
                
                # Projection Data Summary
                f.write("Projection Data Summary:\n")
                f.write("-" * 20 + "\n")
                if metadata['projection_data']:
                    first_proj = metadata['projection_data'][0]
                    last_proj = metadata['projection_data'][-1]
                    f.write("Total Projections: {0}\n".format(len(metadata['projection_data'])))
                    f.write("First Projection Date: {0}\n".format(first_proj['date']))
                    f.write("Last Projection Date: {0}\n".format(last_proj['date']))
                    
                    # Write axis positions for first and last projections
                    f.write("\nFirst Projection Axis Positions:\n")
                    for key, value in first_proj.items():
                        if '_pos' in key:
                            f.write("{0}: {1}\n".format(key, value))
                            
                    f.write("\nLast Projection Axis Positions:\n")
                    for key, value in last_proj.items():
                        if '_pos' in key:
                            f.write("{0}: {1}\n".format(key, value))
                
            print("Metadata text file saved to: {0}".format(txt_path))
            return True
        except Exception as e:
            error_msg = "Error saving metadata text file: {0}".format(str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return False

    def save_cumulative_csv(self):
        """Save all collected metadata to a single CSV file"""
        if not self.all_metadata:
            return False
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(self.output_dir, "cumulative_metadata_{0}.csv".format(timestamp))
        
        try:
            # Prepare flattened data for CSV
            flattened_data = []
            for metadata in self.all_metadata:
                row = {}
                # Add file path
                row['file_path'] = metadata.get('file_path', '')
                
                # Add basic info
                for key, value in metadata['basic_info'].items():
                    row['basic_' + key] = value
                
                # Add machine settings
                for key, value in metadata['machine_settings'].items():
                    row['machine_' + key] = value
                
                # Add image properties
                for key, value in metadata['image_properties'].items():
                    row['image_' + key] = value
                
                # Add first and last projection data
                if metadata['projection_data']:
                    first_proj = metadata['projection_data'][0]
                    last_proj = metadata['projection_data'][-1]
                    
                    for key, value in first_proj.items():
                        row['first_proj_' + key] = value
                    
                    for key, value in last_proj.items():
                        row['last_proj_' + key] = value
                
                flattened_data.append(row)
            
            # Write to CSV
            if flattened_data:
                fieldnames = flattened_data[0].keys()
                with open(csv_path, 'wb') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(flattened_data)
                
                print("\nCumulative metadata saved to: {0}".format(csv_path))
                return True
                
        except Exception as e:
            error_msg = "Error saving cumulative CSV: {0}".format(str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return False

    def process_single_file(self, file_path):
        try:
            print("\nProcessing: {0}".format(file_path))
            
            # Get metadata
            metadata = self.metadata_extractor.get_complete_metadata(file_path)
            if not metadata:
                return False
                
            # Add file path to metadata
            metadata['file_path'] = file_path
            
            # Save metadata as text file next to TXRM file
            if not self.save_metadata_txt(metadata, file_path):
                return False
            
            # Store metadata for cumulative CSV
            self.all_metadata.append(metadata)
            
            # Generate config file
            config_path = os.path.splitext(file_path)[0] + "_config.txt"
            if self.config_converter.create_config_from_txrm(file_path):
                if self.config_converter.save_config(config_path):
                    print("Configuration saved to: {0}".format(config_path))
                else:
                    print("Failed to save configuration file!")
            else:
                print("Failed to create configuration!")
            
            return True
            
        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return False
        finally:
            gc.collect() 