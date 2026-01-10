"""MyWhoosh service for handling authentication and activity downloads."""

import os
import time
import uuid
import tempfile
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime


class MyWhooshService:
    """Service for interacting with MyWhoosh API."""

    def __init__(self, email: str, password: str):
        """Initialize MyWhooshService with credentials.

        Args:
            email: MyWhoosh account email
            password: MyWhoosh account password
        """
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.whoosh_id: Optional[str] = None
        self.device_id: str = str(uuid.uuid4())
        self.logger = logging.getLogger(__name__)

    def authenticate(self) -> None:
        """Authenticate with MyWhoosh.

        Raises:
            RuntimeError: If authentication fails
        """
        self.logger.info(f"Authenticating with MyWhoosh as {self.email}...")

        payload = {
            "Username": self.email,
            "Password": self.password,
            "Platform": "Android",
            "Action": 1001,
            "CorrelationId": str(uuid.uuid4()),
            "DeviceId": self.device_id,
            "Authorization": ""
        }

        try:
            response = requests.post(
                "https://services.mywhoosh.com/http-service/api/login",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("Success"):
                self.access_token = data.get("AccessToken")
                self.whoosh_id = data.get("WhooshId")
                self.refresh_token = data.get("RefreshToken")
                
                self.logger.info(f"Successfully authenticated with MyWhoosh")
                self.logger.info(f"WhooshId: {self.whoosh_id}")
                if self.access_token:
                    self.logger.debug(f"Access token: {self.access_token[:50]}...")

            else:
                message = data.get("Message", "Unknown error")
                self.logger.error(f"Authentication failed: {message}")
                raise RuntimeError(f"Authentication failed: {message}")

        except requests.RequestException as e:
            self.logger.exception(f"Network error during authentication: {e}")
            raise RuntimeError(f"Network error during authentication: {e}") from e
        except Exception as e:
            self.logger.exception(f"Failed to authenticate with MyWhoosh: {e}")
            raise RuntimeError(f"Authentication failed: {e}") from e

    def get_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch activities from MyWhoosh.

        Args:
            limit: Maximum number of activities to fetch

        Returns:
            List of activity dictionaries

        Raises:
            RuntimeError: If not authenticated or fetch fails
        """
        if not self.access_token:
            raise RuntimeError("Must authenticate before fetching activities")

        self.logger.info("Fetching activities from MyWhoosh...")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MyWhoosh-Python-Client/1.0"
        }

        # Try different payload strategies
        payloads_to_try = [
            {},  # Empty payload
            {"limit": limit, "offset": 0},  # Simple pagination
            {"page": 1, "limit": limit},  # Alternative pagination
        ]

        last_error = None
        
        for i, payload in enumerate(payloads_to_try, 1):
            try:
                self.logger.debug(f"Trying payload strategy {i}/{len(payloads_to_try)}: {payload}")
                
                response = requests.post(
                    "https://service14.mywhoosh.com/v2/rider/profile/activities",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    self.logger.debug(f"Response structure: {list(data.keys())}")
                    
                    # Try to extract activities from various possible response structures
                    activities = (
                        data.get('activities') or 
                        data.get('data') or 
                        data.get('rides') or
                        data.get('rideHistory') or
                        []
                    )
                    
                    # If data itself is a list, use it directly
                    if isinstance(data, list):
                        activities = data
                    
                    self.logger.info(f"Found {len(activities)} activities")
                    return activities

                elif response.status_code == 401:
                    self.logger.warning("Token expired, re-authenticating...")
                    self.authenticate()
                    # Retry with new token
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    continue

                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    self.logger.warning(f"Payload {payload} failed: {last_error}")
                    continue

            except requests.RequestException as e:
                last_error = str(e)
                self.logger.warning(f"Payload {payload} failed with network error: {e}")
                continue
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Payload {payload} failed: {e}")
                continue

        # If we get here, all strategies failed
        error_msg = f"Could not fetch activities. Last error: {last_error}"
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    def get_latest_activity(self) -> Optional[Dict[str, Any]]:
        """Get the most recent activity.

        Returns:
            Latest activity dictionary or None if no activities found

        Raises:
            RuntimeError: If not authenticated or fetch fails
        """
        activities = self.get_activities(limit=1)
        
        if not activities:
            self.logger.info("No activities found")
            return None

        latest = activities[0]
        
        # Log activity details
        activity_id = latest.get('id', latest.get('_id', 'unknown'))
        activity_name = latest.get('name', latest.get('title', 'Unknown Activity'))
        activity_date = latest.get('date', latest.get('startTime', latest.get('createdAt', 'unknown')))
        
        self.logger.info(f"Latest activity: {activity_name}")
        self.logger.info(f"Activity ID: {activity_id}")
        self.logger.info(f"Activity date: {activity_date}")
        
        return latest

    def download_activity(self, activity: Dict[str, Any]) -> str:
        """Download activity FIT file.

        Args:
            activity: Activity dictionary from get_activities()

        Returns:
            Path to downloaded FIT file

        Raises:
            RuntimeError: If download fails
        """
        activity_id = activity.get('id', activity.get('_id', 'unknown'))
        self.logger.info(f"Downloading activity {activity_id}...")

        # Try to find download URL in various possible keys
        download_url = (
            activity.get('downloadUrl') or 
            activity.get('fitFileUrl') or
            activity.get('fileUrl') or
            activity.get('s3Url') or
            activity.get('fitFile')
        )

        # If no direct URL, try to construct it
        if not download_url:
            user_id = activity.get('userId', self.whoosh_id)
            file_key = activity.get('fileKey') or activity.get('fitFileKey') or activity.get('key')
            
            if file_key:
                # Try to construct S3 URL
                # Note: This may need AWS signature - the activity might contain signed URL parts
                download_url = f"https://mywhooshprod.s3.eu-west-1.amazonaws.com/ride/{user_id}/{file_key}"
                self.logger.info(f"Constructed S3 URL: {download_url}")
            else:
                # Log the activity structure to help debug
                self.logger.error(f"Cannot find download URL. Activity keys: {list(activity.keys())}")
                raise ValueError(
                    f"No download URL found in activity data. "
                    f"Available keys: {list(activity.keys())}"
                )

        self.logger.info(f"Download URL: {download_url}")

        try:
            # Download the file
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()

            file_size = len(response.content)
            self.logger.info(f"Downloaded {file_size:,} bytes")

            # Determine file extension from Content-Type or URL
            content_type = response.headers.get('Content-Type', '')
            is_dms = '.dms' in download_url.lower() or 'dms' in content_type.lower()

            # Save to temporary directory
            timestamp = int(time.time())
            temp_dir = tempfile.gettempdir()
            
            # Save with appropriate extension
            if is_dms:
                file_path = os.path.join(temp_dir, f"mywhoosh_{activity_id}_{timestamp}.dms")
            else:
                file_path = os.path.join(temp_dir, f"mywhoosh_{activity_id}_{timestamp}.fit")

            with open(file_path, 'wb') as f:
                f.write(response.content)

            self.logger.info(f"Saved to: {file_path}")

            # If it's a .dms file, rename to .fit
            if file_path.endswith('.dms'):
                fit_file_path = file_path.replace('.dms', '.fit')
                os.rename(file_path, fit_file_path)
                self.logger.info(f"Renamed .dms to .fit: {fit_file_path}")
                file_path = fit_file_path

            # Verify it's a valid FIT file
            with open(file_path, 'rb') as f:
                header = f.read(14)  # FIT header is 14 bytes
                
                # Check for FIT magic bytes at offset 8-11
                if len(header) >= 12:
                    if header[8:12] == b'.FIT':
                        self.logger.info("✓ Valid FIT file header detected")
                    else:
                        self.logger.warning(
                            f"File doesn't have expected FIT magic bytes. "
                            f"Header: {header[:12].hex()}"
                        )
                else:
                    self.logger.warning(f"File too small: {len(header)} bytes")

            return file_path

        except requests.RequestException as e:
            self.logger.exception(f"Failed to download activity: {e}")
            raise RuntimeError(f"Download failed: {e}") from e
        except Exception as e:
            self.logger.exception(f"Error during download: {e}")
            raise RuntimeError(f"Download error: {e}") from e
