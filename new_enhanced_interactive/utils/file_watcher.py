# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import json
import time
from datetime import datetime
from new_enhanced_interactive.utils.github_utils import GitHubManager

class TXRMFileWatcher(object):
    def __init__(self, processor, config):
        self.processor = processor
        self.config = config
        self.processed_files = self._load_processed_files()
        
        # Initialize GitHub manager if enabled
        self.github_manager = None
        if self.config.config.get('github_enabled', False):  # Use get() with default False
            self.github_manager = self._setup_github_manager()
    
    def _load_processed_files(self):
        """Load list of already processed files"""
        try:
            if os.path.exists(self.config.config['processed_files_log']):
                with open(self.config.config['processed_files_log'], 'r') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_processed_files(self):
        """Save list of processed files"""
        try:
            with open(self.config.config['processed_files_log'], 'w') as f:
                json.dump(self.processed_files, f, indent=4)
        except Exception as e:
            print("Error saving processed files log: {0}".format(str(e)))
    
    def _get_new_txrm_files(self):
        """Get list of new TXRM files in watch directory"""
        new_files = []
        try:
            for root, _, files in os.walk(self.config.config['watch_directory']):
                for txrm_file in files:
                    if txrm_file.lower().endswith('.txrm'):
                        if not self.config.config['include_drift_files'] and 'drift' in txrm_file.lower():
                            continue
                        full_path = os.path.join(root, txrm_file)
                        if full_path not in self.processed_files:
                            new_files.append(full_path)
        except Exception as e:
            print("Error scanning directory: {0}".format(str(e)))
        return new_files
    
    def _setup_github_manager(self):
        """Setup GitHub manager with PAT"""
        try:
            # Only proceed if all required GitHub config is present
            github_config = self.config.config.get('github_config', {})
            required_fields = ['token', 'repo_owner', 'repo_name', 'branch']
            
            if not all(github_config.get(field) for field in required_fields):
                print("Incomplete GitHub configuration, running without GitHub integration")
                return None
            
            manager = GitHubManager(
                github_config['repo_path'],
                github_config['branch']
            )
            
            # Set token from config
            manager.set_pat(github_config['token'])
            
            # Setup repository
            if manager.setup_repo(github_config['remote_url']):
                print("GitHub integration successfully configured")
                return manager
            
        except Exception as e:
            print("Error setting up GitHub integration: {0}".format(str(e)))
            print("Continuing without GitHub integration")
        return None
    
    def watch(self):
        """Start watching for new files"""
        print("\nStarting file watch mode...")
        print("Watching directory: {0}".format(self.config.config['watch_directory']))
        print("Polling interval: {0} seconds".format(self.config.config['polling_interval']))
        
        if self.github_manager:
            print("GitHub integration enabled")
        
        while True:
            try:
                if not self._process_new_files():
                    time.sleep(self.config.config['polling_interval'])
                    continue
                
            except KeyboardInterrupt:
                print("\nStopping watch mode...")
                break
            except Exception as e:
                print("Error in watch loop: {0}".format(str(e)))
                time.sleep(self.config.config['polling_interval'])

    def _process_new_files(self):
        """Process any new files found in watch directory"""
        new_files = self._get_new_txrm_files()
        if not new_files:
            return False
        
        print("\nFound {0} new files at {1}".format(
            len(new_files), 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        for file_path in new_files:
            self._process_single_file(file_path)
        
        return True

    def _process_single_file(self, file_path):
        """Process a single TXRM file"""
        print("\nProcessing: {0}".format(file_path))
        if not self.processor.process_single_file(file_path):
            print("Failed to process file: {0}".format(file_path))
            return
        
        self.processed_files.append(file_path)
        self._save_processed_files()
        
        # Save cumulative CSV
        csv_path = self.processor.save_cumulative_csv()
        if not csv_path:
            print("Warning: Failed to generate cumulative CSV file")
            return
        
        print("Cumulative CSV updated: {0}".format(csv_path))
            
        # Only attempt GitHub push if manager is configured
        if self.github_manager:
            commit_message = "Update metadata CSV - New file: {0}".format(
                os.path.basename(file_path)
            )
            
            if self.github_manager.commit_and_push_csv(csv_path, commit_message):
                print("Successfully pushed CSV to GitHub")
            else:
                print("Failed to push CSV to GitHub, continuing processing") 