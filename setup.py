from setuptools import setup, find_packages

setup(
    name="new_enhanced_interactive",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "XradiaPy",  # Main library for TXRM file processing
        "numpy",     # Used in some metadata extraction
        
        # Python 2.7 specific dependencies
        "configparser",  # For Python 2.7 (ConfigParser in stdlib)
        "subprocess32",  # Backport of subprocess from Python 3
        "future",        # For Python 2/3 compatibility features
        
        # Optional GUI dependencies (uncomment if needed)
        # "tkinter",     # For GUI components (built-in for Python 2.7)
    ],
    author="X-radia Metadata Team",
    author_email="your.email@example.com",
    description="Enhanced interactive TXRM metadata processor",
    keywords="txrm, metadata, xradia",
    python_requires=">=2.7, <3",
) 