class ProgressTracker:
    def __init__(self, total_files):
        self.total_files = total_files
        self.processed_files = 0
        self.failed_files = []
        
    def update(self, file_path, success):
        self.processed_files += 1
        if not success:
            self.failed_files.append(file_path)
            
    def get_progress(self):
        return {
            'total': self.total_files,
            'processed': self.processed_files,
            'failed': len(self.failed_files),
            'percentage': (self.processed_files / self.total_files) * 100
        } 