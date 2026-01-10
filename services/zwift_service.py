"""Zwift service for handling authentication and activity downloads."""

import os
import tempfile
import requests
import logging
from typing import Optional, Dict, Any
from zwift import Client as ZwiftClient


class ZwiftService:
    """Service for interacting with Zwift API."""

    def __init__(self, username: str, password: str):
        """Initialize ZwiftService with credentials.

        Args:
            username: Zwift username
            password: Zwift password
        """
        self.username = username
        self.password = password
        self.client: Optional[ZwiftClient] = None
        self.logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        """Authenticate with Zwift."""
        self.logger.info("Authenticating with Zwift...")
        self.client = ZwiftClient(self.username, self.password)
        self.logger.info("Successfully authenticated with Zwift")

    def download_last_activity(self) -> Optional[str]:
        """Downloads the last activity's .fit file from Zwift.

        Returns:
            Path to downloaded .fit file, or None if no activities found

        Raises:
            RuntimeError: If not authenticated or download fails
        """
        if not self.client:
            raise RuntimeError("Must authenticate before downloading activities")

        profile = self.client.get_profile()
        activities = profile.get_activities()

        if not activities:
            self.logger.info("No activities found on Zwift")
            return None

        last_activity = activities[0]  # The most recent activity
        activity_id = last_activity['id']
        self.logger.info(f"Downloading activity {activity_id}...")

        link = f"https://{last_activity['fitFileBucket']}.s3.amazonaws.com/{last_activity['fitFileKey']}"
        self.logger.info(f"Download link: {link}")

        try:
            response = requests.get(link, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download activity: {e}") from e

        # Save the .fit file to a temporary location
        temp_dir = tempfile.gettempdir()
        fit_file_path = os.path.join(temp_dir, f"zwift_activity_{activity_id}.fit")

        with open(fit_file_path, "wb") as file:
            file.write(response.content)

        self.logger.info(f"Activity {activity_id} downloaded to {fit_file_path}")
        return fit_file_path
