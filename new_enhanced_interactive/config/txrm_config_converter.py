import os
from XradiaPy import Data
import ConfigParser

class TXRMConfigConverter(object):
    def __init__(self):
        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.config = None

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