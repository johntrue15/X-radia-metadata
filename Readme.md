# ZEISS X-ray Microscopy Data Processing Tools

A collection of Python tools for processing and analyzing ZEISS X-ray microscopy files (.txrm/.xrm).

## Tools Overview

1. `MetadataExtractor.py` - Focused JSON output with summarized statistics
2. `CompleteAPIMetadataExtractor.py` - Comprehensive CSV output with complete projection data
3. `InteractiveTXRMProcessor.py` - Command-line interface for batch processing files
4. `TXRMProcessorGUI.py` - Graphical interface for file selection and processing
5. `TXRMConfigConverter.py` - Converts .txrm metadata to configuration file format

## Prerequisites

- Python 2.7.14 (specific version required)
- ZEISS Scout-and-Scan™ Control System installed
- XradiaPy libraries (included with Scout-and-Scan™)
- PyCharm Community Edition (recommended IDE)

## Installation

1. Install PyCharm Community Edition
2. Configure PyCharm to use Scout-and-Scan™ Python interpreter:
   ```
   Path: C:\Program Files\Carl Zeiss X-ray Microscopy\Xradia Versa\[version]\ScoutScan\pythonw.exe
   ```

## Tool Descriptions

### MetadataExtractor.py
- Creates single JSON file with metadata
- Includes statistical summaries
- Minimal disk space usage
- Best for quick analysis

### CompleteAPIMetadataExtractor.py
- Creates multiple CSV files
- Complete projection data
- Maximum data extraction
- Best for detailed analysis

### InteractiveTXRMProcessor.py
- Command-line interface
- Batch processing capability
- User control over file processing
- Progress tracking

### TXRMProcessorGUI.py
- Graphical user interface
- Drag-and-drop file selection
- Progress bar and status updates
- Real-time processing feedback

### TXRMConfigConverter.py
- Converts TXRM metadata to config format
- Matches ZEISS configuration structure
- Includes geometry and acquisition settings
- Equipment-specific parameters

## Usage Examples

### JSON Metadata Extraction
```python
from MetadataExtractor import MetadataExtractor

extractor = MetadataExtractor(output_dir="output")
metadata = extractor.get_metadata("path/to/file.txrm")
extractor.save_to_json(metadata, "path/to/file.txrm")
```

### CSV Full Data Extraction
```python
from CompleteAPIMetadataExtractor import CompleteAPIMetadataExtractor

extractor = CompleteAPIMetadataExtractor(output_dir="output")
data = extractor.get_complete_metadata("path/to/file.txrm")
extractor.save_to_csv(data, "base_filename")
```

### Config File Conversion
```python
from TXRMConfigConverter import TXRMConfigConverter

converter = TXRMConfigConverter()
converter.create_config_from_txrm("path/to/file.txrm")
converter.save_config("output_config.txt")
```

## Output Formats

### JSON Output Structure
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
        "voltage_kv": "..."
    },
    "projection_summary": {
        "time_span": {...},
        "exposure_times": {...},
        "axis_ranges": {...}
    }
}
```

### CSV Output Files
1. `basic_info.csv` - File information
2. `machine_settings.csv` - Equipment settings
3. `image_properties.csv` - Resolution and dimensions
4. `projections.csv` - Detailed projection data

### Config File Structure
```ini
[General]
Version=2.8.2.20099
SystemName=ZEISS XRM

[Geometry]
FDD=...
FOD=...
VoxelSizeX=...
VoxelSizeY=...

[CT]
NumberImages=...
RotationSector=...

[Xray]
Voltage=...
Current=...
Filter=...
```

## Error Handling

- All tools include comprehensive error logging
- Errors are saved to log files in output directory
- User-friendly error messages
- Failed operations don't stop batch processing

## Known Limitations

1. Python 2.7.14 requirement
2. Windows OS requirement
3. Scout-and-Scan™ software dependency
4. Large files may require significant processing time
5. Memory usage scales with projection count

## Contributing

When modifying these tools:
1. Maintain Python 2.7 compatibility
2. Test with various file sizes
3. Update error handling
4. Document API changes
5. Test on workstation with ZEISS software

## License

These tools are provided for use with ZEISS X-ray microscopy systems. Usage and distribution should comply with ZEISS software licensing terms.
