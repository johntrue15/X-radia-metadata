# X-radia Metadata Extractor

A Python-based tool for extracting and processing metadata from X-radia TXRM files. This tool provides automated metadata extraction, configuration file generation, and continuous monitoring of TXRM files.

## Prerequisites

- Python 2.7 (required for XradiaPy compatibility)
- PyCharm IDE (recommended)
- Xradia Software Suite installed (for XradiaPy package)
- Git (for version control)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/X-radia-metadata.git
cd X-radia-metadata
```

2. Set up in PyCharm:
   - Open PyCharm
   - File -> Open -> Select the `X-radia-metadata` directory
   - Configure Python Interpreter:
     - File -> Settings -> Project -> Python Interpreter
     - Select Python 2.7 interpreter with XradiaPy package

## Project Structure

```
X-radia-metadata/
├── new_enhanced_interactive/        # Main package
│   ├── config/                      # Configuration handling
│   ├── metadata/                    # Metadata extraction
│   ├── processors/                  # TXRM processing
│   ├── utils/                      # Utility functions
│   └── tests/                      # Test files and mocks
├── scripts/                        # Legacy standalone scripts
└── main.py                         # Entry point
```

## Configuration

### GitHub Integration

1. Create a Personal Access Token:
   - Go to GitHub -> Settings -> Developer settings -> Personal access tokens
   - Generate new token with 'repo' scope
   - Copy the token

2. Configure in `watch_config.py`:
```python
GITHUB_CONFIG = {
    'token': 'your_github_token',
    'repo_owner': 'your_github_username',
    'repo_name': 'your_repo_name',
    'branch': 'main'
}
```

### Path Configuration

In `watch_config.py`, set up your watch directories:
```python
WATCH_CONFIG = {
    'watch_paths': [
        r'C:\Path\To\Your\TXRM\Files',
        # Add more paths as needed
    ],
    'file_pattern': '*.txrm'
}
```

## Usage

### Running in PyCharm

1. Open `main.py`
2. Configure run configuration:
   - Run -> Edit Configurations
   - Add New Configuration -> Python
   - Script path: Select `main.py`
   - Python interpreter: Select Python 2.7

3. Command-line options:
```bash
python main.py [options]
  --watch          Enable continuous monitoring of directories
  --path PATH      Process single directory
  --file FILE      Process single file
  --no-github      Disable GitHub integration
```

### Expected Outputs

For each processed TXRM file, the following outputs are generated:

1. Text Metadata File (`*_metadata.txt`):
   - Located next to the source TXRM file
   - Contains detailed metadata in human-readable format
   - Includes basic info, machine settings, and image properties

2. Configuration File (`*_config.txt`):
   - Located next to the source TXRM file
   - Contains machine configuration parameters

3. Cumulative CSV File:
   - Located in the output directory
   - Combines metadata from all processed files
   - Filename format: `cumulative_metadata_YYYYMMDD_HHMMSS.csv`
   - Contains standardized columns for all metadata fields

### Column Descriptions in CSV

- `file_name`: Name of the TXRM file without extension
- `ct_voxel_size_um`: Voxel size in micrometers
- `ct_objective`: Objective lens used
- `xray_tube_voltage`: X-ray tube voltage
- `xray_tube_power`: X-ray tube power
- `xray_tube_current`: Calculated current (power/voltage * 100)
- (See code documentation for complete column list)

## Troubleshooting

1. XradiaPy Import Error:
   - Ensure Xradia software is installed
   - Verify Python 2.7 is being used
   - Check PYTHONPATH includes Xradia installation directory

2. Permission Issues:
   - Run PyCharm as administrator
   - Check file/directory permissions

3. GitHub Integration Issues:
   - Verify token permissions
   - Check network connectivity
   - Ensure correct repository configuration

## Legacy Scripts

The `scripts/` directory contains standalone versions of the metadata extractor:
- `MetadataExtractor.py`: Basic metadata extraction
- `InteractiveTXRMProcessor.py`: Interactive processing
- `enhanced_interactive.py`: Enhanced interactive version
- `CompleteAPIMetadataExtractor.py`: Complete API implementation

These are maintained for reference but the main functionality has been integrated into the new package structure.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here]
