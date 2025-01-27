# ZEISS X-ray Microscopy Metadata Extractors

This repository contains two Python scripts for extracting metadata from ZEISS X-ray microscopy files (.txrm/.xrm):

1. `MetadataExtractor.py` - Focused JSON output with summarized statistics
2. `CompleteAPIMetadataExtractor.py` - Comprehensive CSV output with complete projection data

## Prerequisites

- Python 2.7.14 (specifically this version)
- ZEISS Scout-and-Scan™ Control System installed
- XradiaPy libraries (comes with Scout-and-Scan™ installation)

## Installation

1. Install PyCharm Community Edition
2. Configure PyCharm to use the Python interpreter from Scout-and-Scan™:
   ```
   Default location: C:\Program Files\Carl Zeiss X-ray Microscopy\Xradia Versa\[version_number]\ScoutScan\pythonw.exe
   ```

## MetadataExtractor.py

### Purpose
Creates a single, comprehensive JSON file containing metadata with summarized statistics.

### Features
- Single JSON output file
- Statistical summaries of projection data
- Hierarchical organization of metadata
- Minimal disk space usage
- Human-readable output

### Output Structure
```json
{
    "file_info": {
        "file_path": "...",
        "file_name": "...",
        "acquisition_complete": true/false
    },
    "machine_settings": {
        "objective": "...",
        "pixel_size_um": "...",
        "power_watts": "...",
        "voltage_kv": "...",
        "filter": "...",
        "binning": "..."
    },
    "image_properties": {
        "height_pixels": "...",
        "width_pixels": "...",
        "total_projections": "..."
    },
    "projection_summary": {
        "time_span": {...},
        "exposure_times": {...},
        "axis_ranges": {...}
    }
}
```

### Usage
```python
extractor = MetadataExtractor(output_dir="output")
metadata = extractor.get_metadata("path/to/file.txrm")
extractor.save_to_json(metadata, "path/to/file.txrm")
```

## CompleteAPIMetadataExtractor.py

### Purpose
Extracts every possible metadata field according to the ZEISS API documentation, with complete projection-by-projection data.

### Features
- Multiple CSV output files
- Complete projection data
- Raw data preservation
- Follows API documentation structure
- Maximum data extraction

### Output Files
1. `basic_info.csv` - File information
2. `machine_settings.csv` - Microscope settings
3. `image_properties.csv` - Image dimensions and properties
4. `projections.csv` - Detailed data for each projection
5. `axes.txt` - List of available axes

### Usage
```python
extractor = CompleteAPIMetadataExtractor(output_dir="output")
data = extractor.get_complete_metadata("path/to/file.txrm")
extractor.save_to_csv(data, "base_filename")
```

## Key Differences

| Feature | MetadataExtractor | CompleteAPIMetadataExtractor |
|---------|------------------|----------------------------|
| Output Format | Single JSON | Multiple CSVs |
| Data Detail | Summarized | Complete |
| Projection Data | Statistical Summary | Raw Data |
| File Size | Smaller | Larger |
| Use Case | Quick Analysis | Detailed Analysis |

## Error Handling

Both extractors include:
- Comprehensive error logging
- Progress reporting
- File existence checks
- Exception handling for each metadata field

## Known Limitations

1. Requires Scout-and-Scan™ Control System
2. Python 2.7.14 specific
3. Windows-only (due to ZEISS software requirements)
4. Large files may require significant processing time
5. Memory usage scales with projection count

## Contributing

When modifying these extractors:
1. Maintain Python 2.7 compatibility
2. Test with varying file sizes
3. Update error handling as needed
4. Document any API changes
5. Test on workstation with ZEISS software installed

## License

These scripts are provided for use with ZEISS X-ray microscopy systems. Usage and distribution should comply with ZEISS software licensing terms.
