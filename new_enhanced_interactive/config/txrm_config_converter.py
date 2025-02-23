# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import ConfigParser
from XradiaPy import Data

class TXRMConfigConverter(object):
    def __init__(self):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.config = None

    def _init_config_sections(self):
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
        num_projections = self.dataset.GetProjections()
        self.config.set('CT', 'NumberImages', str(num_projections))
        self.config.set('CT', 'Type', '0')
        self.config.set('CT', 'RotationSector', '360.00000000')
        self.config.set('CT', 'NrImgDone', str(num_projections))

    def _fill_image_section(self):
        self.config.set('Image', 'Width', str(self.dataset.GetWidth()))
        self.config.set('Image', 'Height', str(self.dataset.GetHeight()))

    def _fill_detector_section(self):
        self.config.set('Detector', 'Binning', str(self.dataset.GetBinning()))

    def _fill_axis_section(self):
        axis_names = self.dataset.GetAxesNames()
        for axis in axis_names:
            self.config.set('Axis', axis, '0.0')

    def _fill_general_section(self):
        self.config.set('General', 'Version', '1.0')

    def create_config_from_txrm(self, txrm_path):
        try:
            self.config = ConfigParser.ConfigParser()
            self.dataset.ReadFile(txrm_path)
            self._init_config_sections()
            self._fill_geometry_section()
            self._fill_ct_and_xray_section()
            self._fill_image_section()
            self._fill_detector_section()
            self._fill_axis_section()
            self._fill_general_section()
            return True
        except Exception as e:
            print("Error processing TXRM file: {0}".format(str(e)))
            return False

    def save_config(self, output_path):
        try:
            with open(output_path, 'w') as configfile:
                self.config.write(configfile)
            return True
        except Exception as e:
            print("Error saving config file: {0}".format(str(e)))
            return False

    # ... (rest of the config converter methods) 