#!/usr/bin/env python3
"""
MyWhoosh to Garmin Connect Activity Sync

Fetches the latest activity from MyWhoosh, modifies the device type to Garmin Edge 840,
and uploads it to Garmin Connect with automatic duplicate detection.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

from services.mywhoosh_service import MyWhooshService
from services.fit_file_service import FitFileService
from services.garmin_service import GarminService
from services.activity_processor import ActivityProcessor


def setup_logging(log_level: str = 'INFO') -> None:
    """Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_format = (
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler('mywhoosh_to_garmin.log')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def load_config() -> dict:
    """Load configuration from environment variables.
    
    Returns:
        Dictionary with configuration values
        
    Raises:
        ValueError: If required configuration is missing
    """
    load_dotenv()
    
    config = {
        'mywhoosh_email': os.getenv('MYWHOOSH_EMAIL'),
        'mywhoosh_password': os.getenv('MYWHOOSH_PASSWORD'),
        'garmin_username': os.getenv('GARMIN_USERNAME'),
        'garmin_password': os.getenv('GARMIN_PASSWORD'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    }
    
    # Validate required configuration
    required_keys = [
        'mywhoosh_email',
        'mywhoosh_password',
        'garmin_username',
        'garmin_password'
    ]
    
    missing = [k for k in required_keys if not config[k]]
    
    if missing:
        missing_vars = [k.upper() for k in missing]
        raise ValueError(
            f"Missing required configuration: {', '.join(missing_vars)}\n"
            f"Please check your .env file. See .env.example for reference."
        )
    
    return config


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0=success, 1=failure, 2=config error)
    """
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(config['log_level'])
        logger = logging.getLogger(__name__)
        
        # Application header
        logger.info("=" * 80)
        logger.info("MyWhoosh to Garmin Connect Activity Sync")
        logger.info("=" * 80)
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # Initialize services
        logger.info("Initializing services...")
        
        mywhoosh_service = MyWhooshService(
            config['mywhoosh_email'],
            config['mywhoosh_password']
        )
        
        fit_file_service = FitFileService()
        
        garmin_service = GarminService(
            config['garmin_username'],
            config['garmin_password']
        )
        
        logger.info("Services initialized")
        logger.info("")
        
        # Create processor and run
        processor = ActivityProcessor(
            mywhoosh_service,
            fit_file_service,
            garmin_service
        )
        
        success = processor.process_latest_activity(check_duplicates=True)
        
        # Footer
        logger.info("")
        logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if success:
            logger.info("Exiting with success")
            return 0
        else:
            logger.error("Exiting with failure")
            return 1
    
    except ValueError as e:
        # Configuration error
        print(f"\n❌ Configuration Error: {e}\n", file=sys.stderr)
        return 2
    
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user\n", file=sys.stderr)
        return 130
    
    except Exception as e:
        # Setup basic logging if it failed earlier
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.ERROR)
        
        logging.exception(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}\n", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
