from XradiaPy import Data

class MetadataExtractor(object):
    def __init__(self):
        self.dataset = Data.XRMData.XrmBasicDataSet()

    def get_basic_info(self):
        return {
            'file_name': self.dataset.GetName(),
            'initialized_correctly': self.dataset.IsInitializedCorrectly()
        }

    def get_machine_settings(self):
        return {
            'objective': self.dataset.GetObjective(),
            'pixel_size': self.dataset.GetPixelSize(),
            'power': self.dataset.GetPower(),
            'voltage': self.dataset.GetVoltage(),
            'filter': self.dataset.GetFilter(),
            'binning': self.dataset.GetBinning()
        }

    def get_image_properties(self):
        return {
            'height': self.dataset.GetHeight(),
            'width': self.dataset.GetWidth(),
            'total_projections': self.dataset.GetProjections()
        }

    def get_axis_positions(self, projection_idx):
        axis_data = {}
        axis_names = self.dataset.GetAxesNames()
        for axis in axis_names:
            pos = self.dataset.GetAxisPosition(projection_idx, axis)
            axis_data["{0}_pos".format(axis.replace(" ", "_"))] = pos
        return axis_data

    def get_projection_data(self, projection_idx):
        proj_data = {
            'projection_number': projection_idx,
            'date': self.dataset.GetDate(projection_idx),
            'detector_to_ra_distance': self.dataset.GetDetectorToRADistance(projection_idx),
            'source_to_ra_distance': self.dataset.GetSourceToRADistance(projection_idx),
            'exposure': self.dataset.GetExposure(projection_idx)
        }
        proj_data.update(self.get_axis_positions(projection_idx))
        return proj_data 