import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(name: str = __name__) -> logging.Logger:
    """Configures and returns a standard logger instance that writes to both console and file with UTF-8 encoding."""
    
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers if called multiple times
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console Handler with UTF-8 stream fallback
        stream = getattr(sys.stdout, 'buffer', sys.stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        logger.addHandler(console_handler)
        
        # File Handler with UTF-8 encoding (10 MB max size, keep 3 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8', errors='replace')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

