# -*- coding: utf-8 -*-
import os
import json

DEFAULT_CONFIG = {
    "watch_mode_enabled": False,
    "watch_directory": "",
    "polling_interval": 60,  # seconds
    "processed_files_log": "processed_files.json",
    "cumulative_csv_path": "",
    "include_drift_files": False,
    "github_enabled": False,
    "github_repo_path": "",
    "github_remote_url": "",
    "github_branch": "main"
}

class WatchConfig(object):
    def __init__(self, config_path="watch_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file or create default"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG
    
    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception:
            return False
    
    def update_config(self, **kwargs):
        """Update configuration with new values"""
        self.config.update(kwargs)
        self.save_config() 