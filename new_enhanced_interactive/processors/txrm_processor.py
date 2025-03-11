# -*- coding: utf-8 -*-
from __future__ import print_function, division
import os
import csv
from datetime import datetime
import gc
import time

# Fix the imports to use absolute imports from the package root
from new_enhanced_interactive.config.txrm_config_converter import TXRMConfigConverter
from new_enhanced_interactive.metadata.metadata_extractor import MetadataExtractor
from new_enhanced_interactive.utils.logging_utils import setup_logger
from new_enhanced_interactive.utils.validation_utils import TXRMValidator

class TXRMProcessor(object):
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                print("Warning: Could not create output directory: {}".format(str(e)))
        
        self.all_metadata = []  # Store metadata from all processed files
        self.config_converter = TXRMConfigConverter()
        self.metadata_extractor = MetadataExtractor()
        self.validator = TXRMValidator()
        self.logger = setup_logger('txrm_processor')

    def save_metadata_txt(self, metadata, file_path):
        """Save metadata as formatted text file next to TXRM file"""
        txt_path = os.path.splitext(file_path)[0] + "_metadata.txt"
        try:
            with open(txt_path, 'w') as f:
                # Write file info
                f.write("TXRM File Metadata\n")
                f.write("=" * 50 + "\n\n")
                
                # File Hash
                f.write("File Information:\n")
                f.write("-" * 20 + "\n")
                f.write("SHA-256 Hash: %s\n" % metadata['file_hash'])
                f.write("File Size: %s bytes\n" % metadata['validation_info'].get('size', 'Unknown'))
                f.write("Validated At: %s\n\n" %
                    time.strftime('%Y-%m-%d %H:%M:%S', 
                    time.localtime(metadata['validation_info'].get('validated_at', 0))))
                
                # Basic Info
                f.write("Basic Information:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['basic_info'].items():
                    f.write("%s: %s\n" % (key, value))
                f.write("\n")
                
                # Machine Settings
                f.write("Machine Settings:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['machine_settings'].items():
                    f.write("%s: %s\n" % (key, value))
                f.write("\n")
                
                # Image Properties
                f.write("Image Properties:\n")
                f.write("-" * 20 + "\n")
                for key, value in metadata['image_properties'].items():
                    f.write("%s: %s\n" % (key, value))
                f.write("\n")
                
                # Projection Data Summary
                f.write("Projection Data Summary:\n")
                f.write("-" * 20 + "\n")
                if metadata['projection_data']:
                    first_proj = metadata['projection_data'][0]
                    last_proj = metadata['projection_data'][-1]
                    f.write("Total Projections: %s\n" % len(metadata['projection_data']))
                    f.write("First Projection Date: %s\n" % first_proj['date'])
                    f.write("Last Projection Date: %s\n" % last_proj['date'])
                    
                    # Write axis positions for first and last projections
                    f.write("\nFirst Projection Axis Positions:\n")
                    for key, value in first_proj.items():
                        if '_pos' in key:
                            f.write("%s: %s\n" % (key, value))
                            
                    f.write("\nLast Projection Axis Positions:\n")
                    for key, value in last_proj.items():
                        if '_pos' in key:
                            f.write("%s: %s\n" % (key, value))
            
            self.logger.info("Metadata text file saved to: %s", txt_path)
            return True
        
        except Exception as e:
            error_msg = "Error saving metadata text file: %s" % str(e)
            self.logger.error(error_msg)
            print(error_msg)
            return False

    def _get_file_name(self, m):
        """Get file name without extension"""
        return os.path.splitext(os.path.basename(m.get('file_path', '')))[0]

    def _get_file_path(self, m):
        """Get file path"""
        return m.get('file_path', '')

    def save_cumulative_csv(self):
        """Save all collected metadata to a single CSV file with specified column order"""
        if not self.all_metadata:
            self.logger.warning("No metadata to save to cumulative CSV")
            return False
        
        # Define column order and mappings with clear descriptions
        column_order = [
            # File Information
            ('file_name', self._get_file_name),
            ('file_hash', lambda m: m.get('file_hash', '')),
            ('file_size_bytes', lambda m: str(m['validation_info'].get('size', ''))),
            ('validation_timestamp', lambda m: time.strftime('%Y-%m-%d %H:%M:%S', 
                time.localtime(m['validation_info'].get('validated_at', 0)))),
            ('file_path', lambda m: os.path.dirname(m.get('file_path', ''))),
            ('txrm_file_path', self._get_file_path),
            ('acquisition_successful', lambda m: str(m['basic_info'].get('initialized_correctly', 'False'))),
            
            # Machine Settings
            ('ct_voxel_size_um', lambda m: str(m['machine_settings'].get('pixel_size', '0.0'))),
            ('ct_objective', lambda m: str(m['machine_settings'].get('objective', ''))),
            ('ct_number_images', lambda m: str(m['image_properties'].get('total_projections', '0'))),
            ('ct_optical_magnification', lambda m: 'yes' if str(m['machine_settings'].get('objective', '')).lower() in ['4x', '20x', '40x'] else 'no'),
            ('xray_tube_voltage', lambda m: str(m['machine_settings'].get('voltage', '0.0'))),
            ('xray_tube_power', lambda m: str(m['machine_settings'].get('power', '0.0'))),
            ('xray_tube_current', self._calculate_xray_current),
            ('xray_filter', lambda m: str(m['machine_settings'].get('filter', ''))),
            
            # Detector Settings
            ('detector_binning', lambda m: str(m['machine_settings'].get('binning', '0'))),
            ('detector_capture_time', lambda m: str(m['projection_data'][0].get('exposure', '0.0')) if m.get('projection_data') else '0.0'),
            ('detector_averaging', lambda m: str(len(m.get('projection_data', []))) if m.get('projection_data') else '0'),
            
            # Image Properties
            ('image_width_pixels', lambda m: str(m['image_properties'].get('width', '0'))),
            ('image_height_pixels', lambda m: str(m['image_properties'].get('height', '0'))),
            ('image_width_real', lambda m: self._calculate_real_dimension(m, 'width')),
            ('image_height_real', lambda m: self._calculate_real_dimension(m, 'height')),
            
            # Time Information
            ('scan_time', self._calculate_scan_time),
            ('start_time', lambda m: str(m['projection_data'][0].get('date', '')) if m.get('projection_data') else ''),
            ('end_time', lambda m: str(m['projection_data'][-1].get('date', '')) if m.get('projection_data') else '')
        ]

        # Add all axis-related columns with proper formatting
        axes = [
            ('Sample X', 'Sample_X_pos'),
            ('Sample Y', 'Sample_Y_pos'),
            ('Sample Z', 'Sample_Z_pos'),
            ('Sample Theta', 'Sample_Theta_pos'),
            ('Source X', 'Source_X_pos'),
            ('Source Z', 'Source_Z_pos'),
            ('Flat Panel Z', 'Flat_Panel_Z_pos'),
            ('Flat Panel X', 'Flat_Panel_X_pos'),
            ('Detector Z', 'Detector_Z_pos'),
            ('CCD Z', 'CCD_Z_pos'),
            ('CCD X', 'CCD_X_pos'),
            ('MkIV Filter Wheel', 'MkIV_Filter_Wheel_pos'),
            ('DCT', 'DCT_pos')
        ]
        
        for display_name, metadata_name in axes:
            safe_name = display_name.lower().replace(' ', '_')
            column_order.extend([
                ('{0}_start'.format(safe_name), lambda m, name=metadata_name: self._get_axis_position(m, name, 0)),
                ('{0}_end'.format(safe_name), lambda m, name=metadata_name: self._get_axis_position(m, name, -1)),
                ('{0}_range'.format(safe_name), lambda m, name=metadata_name: self._calculate_axis_range_new(m, name))
            ])

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                self.logger.info("Created output directory: %s", self.output_dir)
            except Exception as e:
                error_msg = "Error creating output directory: %s" % str(e)
                self.logger.error(error_msg)
                print(error_msg)
                return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(self.output_dir, "cumulative_metadata_{0}.csv".format(timestamp))
        
        try:
            # Prepare data with specified column order
            rows = []
            for metadata in self.all_metadata:
                row = {}
                for column_name, value_func in column_order:
                    try:
                        value = value_func(metadata)
                        # Ensure numeric values are properly formatted
                        if isinstance(value, float):
                            row[column_name] = "{0:.6f}".format(value)
                        else:
                            row[column_name] = str(value) if value is not None else ''
                    except Exception as e:
                        self.logger.warning("Error getting value for %s: %s", column_name, str(e))
                        row[column_name] = ''
                rows.append(row)

            # Write to CSV with specified column order
            fieldnames = [col[0] for col in column_order]
            
            with open(csv_path, 'w') as csvfile:  # Changed from 'wb' to 'w' for better compatibility
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
                
            self.logger.info("Cumulative metadata saved to: %s", csv_path)
            print("\nCumulative metadata saved to: {}".format(csv_path))
            return csv_path
            
        except Exception as e:
            error_msg = "Error saving cumulative CSV: %s" % str(e)
            self.logger.error(error_msg, exc_info=True)
            print(error_msg)
            return False

    def _calculate_xray_current(self, metadata):
        """Safely calculate X-ray tube current"""
        try:
            power = float(metadata['machine_settings'].get('power', 0))
            voltage = float(metadata['machine_settings'].get('voltage', 0))
            if voltage > 0:
                return str(round((power / voltage) * 100, 2))
            return ''
        except (ValueError, TypeError, ZeroDivisionError):
            return ''

    def _calculate_real_dimension(self, metadata, dimension):
        """Safely calculate real dimension"""
        try:
            pixels = float(metadata['image_properties'].get(dimension, 0))
            pixel_size = float(metadata['machine_settings'].get('pixel_size', 0))
            if pixels > 0 and pixel_size > 0:
                return str(round(pixels * pixel_size, 2))
            return ''
        except (ValueError, TypeError):
            return ''

    def _calculate_scan_time(self, metadata):
        """Safely calculate scan time"""
        try:
            if not metadata.get('projection_data'):
                return ''
            start_time = metadata['projection_data'][0].get('date')
            end_time = metadata['projection_data'][-1].get('date')
            if start_time and end_time:
                time_diff = end_time - start_time
                return str(time_diff)
            return ''
        except (IndexError, TypeError, ValueError):
            return ''

    def _get_axis_position(self, metadata, axis_name, index):
        """Get axis position with improved precision"""
        try:
            if metadata.get('projection_data'):
                pos = metadata['projection_data'][index].get(axis_name)
                if pos is not None:
                    return "{0:.6f}".format(float(pos))
            return '0.0'
        except (KeyError, IndexError, ValueError) as e:
            self.logger.debug("Error getting position for %s: %s", axis_name, str(e))
            return '0.0'

    def _calculate_axis_range_new(self, metadata, axis_name):
        """Calculate axis range with improved precision"""
        try:
            if not metadata.get('projection_data'):
                return '0.0'
            start_pos = float(metadata['projection_data'][0].get(axis_name, 0))
            end_pos = float(metadata['projection_data'][-1].get(axis_name, 0))
            range_value = abs(end_pos - start_pos)
            return "{0:.6f}".format(range_value)
        except (ValueError, TypeError, IndexError) as e:
            self.logger.debug("Error calculating range for %s: %s", axis_name, str(e))
            return '0.0'

    def process_single_file(self, file_path):
        try:
            print("\nProcessing: %s", file_path)
            
            # Validate file and get hash
            valid, message, file_hash = self.validator.validate_file(file_path)
            if not valid:
                error_msg = "File validation failed: %s" % message
                self.logger.error(error_msg)
                print(error_msg)
                return False
                
            # Log file hash
            self.logger.info("File hash (SHA-256): %s", file_hash)
            
            # Get metadata
            metadata = self.metadata_extractor.get_complete_metadata(file_path)
            if not metadata:
                return False
                
            # Add file path and hash to metadata
            metadata['file_path'] = file_path
            metadata['file_hash'] = file_hash
            metadata['validation_info'] = self.validator.get_validation_info(file_path)
            
            # Save metadata as text file next to TXRM file
            if not self.save_metadata_txt(metadata, file_path):
                return False
            
            # Store metadata for cumulative CSV
            self.all_metadata.append(metadata)
            
            # Generate config file
            config_path = os.path.splitext(file_path)[0] + "_config.txt"
            if self.config_converter.create_config_from_txrm(file_path, metadata=metadata):
                if self.config_converter.save_config(config_path):
                    self.logger.info("Configuration saved to: %s", config_path)
                else:
                    self.logger.error("Failed to save configuration file")
            else:
                self.logger.error("Failed to create configuration")
            
            return True
            
        except Exception as e:
            error_msg = "Error processing file %s: %s" % (file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return False
        finally:
            gc.collect() 