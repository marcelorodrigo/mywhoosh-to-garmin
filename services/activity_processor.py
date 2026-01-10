"""Activity processor for orchestrating the MyWhoosh to Garmin workflow."""

import logging
from typing import Optional
from datetime import datetime
from services.mywhoosh_service import MyWhooshService
from services.fit_file_service import FitFileService
from services.garmin_service import GarminService


class ActivityProcessor:
    """Main orchestrator for processing activities from MyWhoosh to Garmin."""

    def __init__(self,
                 mywhoosh_service: MyWhooshService,
                 fit_file_service: FitFileService,
                 garmin_service: GarminService):
        """Initialize ActivityProcessor with injected services.

        Args:
            mywhoosh_service: Service for MyWhoosh operations
            fit_file_service: Service for FIT file operations
            garmin_service: Service for Garmin operations
        """
        self.mywhoosh_service = mywhoosh_service
        self.fit_file_service = fit_file_service
        self.garmin_service = garmin_service
        self.logger = logging.getLogger(__name__)

    def process_latest_activity(self, check_duplicates: bool = True) -> bool:
        """Process the latest activity from MyWhoosh to Garmin.

        Args:
            check_duplicates: Whether to check for duplicate activities on Garmin

        Returns:
            True if successful, False otherwise
        """
        original_file_path: Optional[str] = None
        modified_file_path: Optional[str] = None

        try:
            # Header
            self.logger.info("=" * 70)
            self.logger.info("MyWhoosh to Garmin Connect Activity Sync")
            self.logger.info("=" * 70)

            # Step 1: Authenticate with MyWhoosh
            self.logger.info("Step 1: Authenticating with MyWhoosh...")
            self.mywhoosh_service.authenticate()

            # Step 2: Get latest activity
            self.logger.info("Step 2: Fetching latest activity...")
            latest_activity = self.mywhoosh_service.get_latest_activity()

            if not latest_activity:
                self.logger.info("No activities found - nothing to sync")
                return False

            # Extract activity metadata for logging and duplicate checking
            activity_id = latest_activity.get('id', latest_activity.get('_id', 'unknown'))
            activity_name = latest_activity.get('name', latest_activity.get('title', 'Unknown Activity'))
            activity_date_str = (
                latest_activity.get('date') or 
                latest_activity.get('startTime') or 
                latest_activity.get('createdAt') or 
                latest_activity.get('timestamp')
            )

            self.logger.info(f"Activity: {activity_name}")
            self.logger.info(f"Activity ID: {activity_id}")
            self.logger.info(f"Activity date: {activity_date_str}")

            # Step 3: Check for duplicates (if enabled)
            if check_duplicates:
                self.logger.info("Step 3: Checking for duplicates on Garmin Connect...")
                
                # Authenticate with Garmin early for duplicate check
                if not self.garmin_service.is_authenticated():
                    self.garmin_service.authenticate()

                # Parse activity date for duplicate checking
                activity_date = self._parse_activity_date(activity_date_str)

                if activity_date:
                    is_duplicate = self.garmin_service.check_duplicate_activity(
                        activity_date,
                        activity_name
                    )

                    if is_duplicate:
                        self.logger.warning("⚠ Duplicate activity found - skipping upload")
                        self.logger.info("=" * 70)
                        self.logger.info("✓ Sync completed (duplicate skipped)")
                        self.logger.info("=" * 70)
                        return True  # Not an error - just skipped
                else:
                    self.logger.warning(
                        f"Could not parse activity date: {activity_date_str}. "
                        f"Continuing with upload..."
                    )
            else:
                self.logger.info("Step 3: Duplicate check disabled - skipping")

            # Step 4: Download activity FIT file
            self.logger.info("Step 4: Downloading activity FIT file...")
            original_file_path = self.mywhoosh_service.download_activity(latest_activity)
            self.logger.info(f"Downloaded to: {original_file_path}")

            # Step 5: Modify FIT file device info
            self.logger.info("Step 5: Modifying FIT file device info...")
            modified_file_path = self.fit_file_service.modify_device_info(original_file_path)
            self.logger.info(f"Modified file: {modified_file_path}")

            # Step 6: Authenticate with Garmin (if not already done)
            if not self.garmin_service.is_authenticated():
                self.logger.info("Step 6: Authenticating with Garmin Connect...")
                self.garmin_service.authenticate()
            else:
                self.logger.info("Step 6: Already authenticated with Garmin Connect")

            # Step 7: Upload to Garmin Connect
            self.logger.info("Step 7: Uploading to Garmin Connect...")
            response = self.garmin_service.upload_activity(modified_file_path)

            # Success!
            self.logger.info("=" * 70)
            self.logger.info("✓ Sync completed successfully!")
            self.logger.info("=" * 70)
            self.logger.debug(f"Upload response: {response}")

            return True

        except Exception as e:
            self.logger.error("=" * 70)
            self.logger.error("✗ Sync failed!")
            self.logger.error("=" * 70)
            self.logger.exception(f"Error: {e}")
            return False

        finally:
            # Cleanup temporary files
            self.logger.info("Cleaning up temporary files...")
            if original_file_path:
                self.fit_file_service.cleanup_file(original_file_path)
            if modified_file_path:
                self.fit_file_service.cleanup_file(modified_file_path)
            self.logger.info("Cleanup complete")

    def _parse_activity_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse activity date from various possible formats.

        Args:
            date_str: Date string in various formats (ISO, timestamp, etc.)

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        # Try parsing as Unix timestamp (numeric)
        try:
            timestamp = float(date_str)
            # Timestamps are typically in seconds, but could be milliseconds
            # If > 100 billion, likely milliseconds
            if timestamp > 100_000_000_000:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp)
        except (ValueError, AttributeError, OSError):
            pass

        # Try different date formats
        date_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',      # ISO with milliseconds and Z
            '%Y-%m-%dT%H:%M:%SZ',          # ISO with Z
            '%Y-%m-%dT%H:%M:%S',           # ISO without Z
            '%Y-%m-%d %H:%M:%S',           # Space separated
            '%Y-%m-%d',                     # Date only
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.replace('+00:00', ''), fmt)
            except (ValueError, AttributeError):
                continue

        # Try isoformat parsing
        try:
            date_str_clean = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str_clean)
        except (ValueError, AttributeError):
            pass

        self.logger.warning(f"Could not parse date: {date_str}")
        return None
