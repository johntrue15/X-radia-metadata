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
        self.all_metadata = []  # Store metadata from all processed files
        self.config_converter = TXRMConfigConverter()
        self.metadata_extractor = MetadataExtractor()
        self.validator = TXRMValidator()  # Add validator
        self.logger = setup_logger(self.output_dir)

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
                f.write("SHA-256 Hash: {0}\n".format(metadata['file_hash']))
                f.write("File Size: {0} bytes\n".format(metadata['validation_info'].get('size', 'Unknown')))
                f.write("Validated At: {0}\n\n".format(
                    time.strftime('%Y-%m-%d %H:%M:%S', 
                    time.localtime(metadata['validation_info'].get('validated_at', 0)))
                ))
                
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

    def _get_file_name(self, m):
        """Get file name without extension"""
        return os.path.splitext(os.path.basename(m.get('file_path', '')))[0]

    def _get_file_path(self, m):
        """Get file path"""
        return m.get('file_path', '')

    def save_cumulative_csv(self):
        """Save all collected metadata to a single CSV file with specified column order"""
        if not self.all_metadata:
            return False
        
        # Define column order and mappings
        column_order = [
            ('file_name', self._get_file_name),
            ('file_hash', lambda m: m.get('file_hash', '')),  # Add hash to CSV
            ('file_size_bytes', lambda m: str(m['validation_info'].get('size', ''))),
            ('validation_timestamp', lambda m: time.strftime('%Y-%m-%d %H:%M:%S', 
                time.localtime(m['validation_info'].get('validated_at', 0)))),
            ('file_hyperlink', self._get_file_path),
            ('ct_voxel_size_um', lambda m: str(m['machine_settings'].get('pixel_size', '')) if m['machine_settings'].get('pixel_size') is not None else ''),
            ('ct_objective', lambda m: str(m['machine_settings'].get('objective', ''))),
            ('ct_number_images', lambda m: str(m['image_properties'].get('total_projections', ''))),
            ('ct_optical_magnification', lambda m: 'yes' if str(m['machine_settings'].get('objective', '')).lower() in ['4x', '20x', '40x'] else 'no'),
            ('xray_tube_voltage', lambda m: str(m['machine_settings'].get('voltage', ''))),
            ('xray_tube_power', lambda m: str(m['machine_settings'].get('power', ''))),
            ('xray_tube_current', self._calculate_xray_current),
            ('xray_filter', lambda m: str(m['machine_settings'].get('filter', ''))),
            ('detector_binning', lambda m: str(m['machine_settings'].get('binning', ''))),
            ('detector_capture_time', lambda m: str(m['projection_data'][0].get('exposure', '')) if m.get('projection_data') else ''),
            ('detector_averaging', lambda m: str(len(m.get('projection_data', []))) if m.get('projection_data') else ''),
            ('image_width_pixels', lambda m: str(m['image_properties'].get('width', ''))),
            ('image_height_pixels', lambda m: str(m['image_properties'].get('height', ''))),
            ('image_width_real', lambda m: self._calculate_real_dimension(m, 'width')),
            ('image_height_real', lambda m: self._calculate_real_dimension(m, 'height')),
            ('scan_time', self._calculate_scan_time),
            ('start_time', lambda m: str(m['projection_data'][0].get('date', '')) if m.get('projection_data') else ''),
            ('end_time', lambda m: str(m['projection_data'][-1].get('date', '')) if m.get('projection_data') else ''),
            ('txrm_file_path', self._get_file_path),
            ('file_path', lambda m: os.path.dirname(m.get('file_path', ''))),
            ('acquisition_successful', lambda m: m['basic_info'].get('initialized_correctly', '')),
        ]

        # Add all axis-related columns
        axes = ['Sample X', 'Sample Y', 'Sample Z', 'Sample Theta', 'Source X', 'Source Z', 
                'Flat Panel Z', 'Flat Panel X', 'Detector Z', 'CCD Z', 'CCD X']
        
        for axis in axes:
            safe_axis = axis.replace(' ', '_')
            column_order.extend([
                ('{0}_start'.format(safe_axis.lower()), lambda m, a=axis: self._get_axis_position(m, a, 0)),
                ('{0}_end'.format(safe_axis.lower()), lambda m, a=axis: self._get_axis_position(m, a, -1)),
                ('{0}_range'.format(safe_axis.lower()), lambda m, a=axis: self._calculate_axis_range(m, a))
            ])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(self.output_dir, "cumulative_metadata_{0}.csv".format(timestamp))
        
        try:
            # Prepare data with specified column order
            rows = []
            for metadata in self.all_metadata:
                row = {}
                for column_name, value_func in column_order:
                    try:
                        row[column_name] = value_func(metadata)
                    except (KeyError, TypeError, ValueError) as e:
                        self.logger.warning("Error getting value for %s: %s", column_name, str(e))
                        row[column_name] = ''
                rows.append(row)

            # Write to CSV with specified column order
            with open(csv_path, 'wb') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=[col[0] for col in column_order])
                writer.writeheader()
                writer.writerows(rows)
                
            print("\nCumulative metadata saved to: {0}".format(csv_path))
            return csv_path
            
        except Exception as e:
            error_msg = "Error saving cumulative CSV: {0}".format(str(e))
            self.logger.error(error_msg)
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

    def _get_axis_position(self, metadata, axis, index):
        """Safely get axis position"""
        try:
            if metadata.get('projection_data'):
                pos = metadata['projection_data'][index].get('{0}_pos'.format(axis.replace(" ", "_")))
                return str(pos) if pos is not None else ''
            return ''
        except (KeyError, IndexError):
            return ''

    def _calculate_axis_range(self, metadata, axis):
        """Safely calculate axis range"""
        try:
            if not metadata.get('projection_data'):
                return ''
            start_pos = metadata['projection_data'][0].get('{0}_pos'.format(axis.replace(" ", "_")))
            end_pos = metadata['projection_data'][-1].get('{0}_pos'.format(axis.replace(" ", "_")))
            if start_pos is not None and end_pos is not None:
                return str(round(abs(float(end_pos) - float(start_pos)), 2))
            return ''
        except (ValueError, TypeError, IndexError):
            return ''

    def process_single_file(self, file_path):
        try:
            print("\nProcessing: {0}".format(file_path))
            
            # Validate file and get hash
            valid, message, file_hash = self.validator.validate_file(file_path)
            if not valid:
                error_msg = "File validation failed: {0}".format(message)
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
                    self.logger.info(f"Configuration saved to: {config_path}")
                else:
                    self.logger.error("Failed to save configuration file")
            else:
                self.logger.error("Failed to create configuration")
            
            return True
            
        except Exception as e:
            error_msg = "Error processing file {0}: {1}".format(file_path, str(e))
            self.logger.error(error_msg)
            print(error_msg)
            return False
        finally:
            gc.collect() 