import time
import os
import json
from datetime import datetime

class BatchTyper:
    """
    Handles incremental typing of content in batches with configurable size and delay.
    Can be integrated with keyboard input systems.
    """
    def __init__(self, batch_size=50, batch_delay=0.1):
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.progress = 0
        self.content = ""
        self.session_file = "typing_session.json"
        self.on_progress_update = None  # Callback function for progress updates
        self.on_status_update = None    # Callback function for status updates

    def load_content(self, content_str=None, file_path=None):
        """Load content from string or file."""
        try:
            if content_str:
                self.content = content_str
            elif file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.content = f.read()
            else:
                self._update_status("No content provided")
                return False
                
            self._update_status(f"Loaded {len(self.content)} characters")
            return True
        except Exception as e:
            self._update_status(f"Error loading content: {e}")
            return False

    def type_content(self, typing_function):
        """
        Types content in batches using the provided typing function.
        
        Parameters:
        - typing_function: Function that accepts a string and types it.
                         It should handle the actual typing mechanism.
        """
        try:
            total_chars = len(self.content)
            
            # Resume progress if available
            start_pos = self.progress
            content = self.content[start_pos:]
            
            self._update_status(f"Starting from position {start_pos}/{total_chars}")
            
            for i in range(0, len(content), self.batch_size):
                batch = content[i:i + self.batch_size]
                
                # Call the provided typing function with the current batch
                typing_function(batch)
                
                # Update progress
                self.progress = start_pos + i + len(batch)
                self._update_progress(self.progress / total_chars)
                
                # Save progress periodically
                if self.progress % (self.batch_size * 5) == 0:
                    self.save_session()
                
                self._update_status(f"Progress: {self.progress}/{total_chars} characters")
                time.sleep(self.batch_delay)
            
            self.save_session()
            self._update_progress(1.0)
            self._update_status("Content typed successfully!")
            return True
        except Exception as e:
            self._update_status(f"Error typing content: {e}")
            self.save_session()
            return False

    def save_session(self):
        """Save current typing progress."""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "progress": self.progress,
                    "timestamp": datetime.now().isoformat()
                }, f)
        except Exception as e:
            self._update_status(f"Failed to save session: {e}")

    def load_session(self, reset=False):
        """Load previous session progress."""
        if reset:
            self.progress = 0
            return False
            
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                self.progress = session_data["progress"]
                if self.progress > 0:
                    self._update_status(f"Found saved progress: {self.progress} characters")
                    return True
        except Exception as e:
            self._update_status(f"Failed to load session: {e}")
        
        self.progress = 0
        return False

    def _update_progress(self, progress_ratio):
        """Update progress using callback if available."""
        if callable(self.on_progress_update):
            self.on_progress_update(progress_ratio)

    def _update_status(self, message):
        """Update status using callback if available."""
        if callable(self.on_status_update):
            self.on_status_update(message)
        else:
            print(message)  # Fallback to console output

# Example usage:
if __name__ == "__main__":
    # This is just a demonstration of how to use the BatchTyper
    def demo_typing_function(text):
        """Example typing function that just prints the text."""
        print(f"TYPING: {text}")
    
    # Create typer instance
    typer = BatchTyper(batch_size=10, batch_delay=0.5)
    
    # Set up custom progress handler (optional)
    typer.on_progress_update = lambda p: print(f"Progress: {p*100:.1f}%")
    
    # Load content
    typer.load_content(content_str="This is a test of the batch typing system. It will type this text in batches.")
    
    # Load any previous session (optional)
    typer.load_session()
    
    # Type the content using our demo function
    typer.type_content(demo_typing_function)