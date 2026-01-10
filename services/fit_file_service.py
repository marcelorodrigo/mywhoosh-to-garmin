"""FIT file service for handling file modifications."""

import os
import tempfile
import logging
from typing import Optional
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import Manufacturer, GarminProduct
from fit_tool.fit_file_builder import FitFileBuilder


class FitFileService:
    """Service for modifying FIT files."""

    def __init__(self):
        """Initialize FitFileService."""
        self.logger = logging.getLogger(__name__)

    def modify_device_info(self, fit_file_path: str,
                          manufacturer: Optional[int] = None,
                          product: Optional[int] = None,
                          software_version: Optional[float] = None) -> str:
        """Modifies the device manufacturer and type in a .fit file.

        Args:
            fit_file_path: Path to the original FIT file
            manufacturer: Device manufacturer (defaults to Garmin - ID 1)
            product: Device product (defaults to Edge 840 - ID 4024)
            software_version: Software version (defaults to 20.19)

        Returns:
            Path to the modified FIT file

        Raises:
            FileNotFoundError: If the input file doesn't exist
            RuntimeError: If file modification fails
        """
        if not os.path.exists(fit_file_path):
            raise FileNotFoundError(f"FIT file not found: {fit_file_path}")

        # Set defaults for Garmin Edge 840
        manufacturer = manufacturer or Manufacturer.GARMIN.value
        product = product or 4024  # Edge 840 (not in GarminProduct enum yet)
        software_version = software_version or 20.19

        self.logger.info(f"Modifying FIT file: {fit_file_path}")
        self.logger.info(
            f"Target device: Garmin Edge 840 "
            f"(manufacturer: {manufacturer}, product: {product}, sw: {software_version})"
        )

        try:
            content = FitFile.from_file(fit_file_path)

            # Set auto_define to true, so that the builder creates the required Definition Messages
            builder = FitFileBuilder(auto_define=True, min_string_size=50)

            for record in content.records:
                message = record.message
                if isinstance(message, FileIdMessage):
                    message.manufacturer = manufacturer
                    message.product = product
                elif isinstance(message, DeviceInfoMessage):
                    message.manufacturer = manufacturer
                    message.product = product
                    message.software_version = software_version
                builder.add(message)

            # Build the FIT file object
            fit_file = builder.build()

            # Save the modified FIT file
            temp_dir = tempfile.gettempdir()
            modified_fit_file_path = os.path.join(temp_dir, "modified_" + os.path.basename(fit_file_path))
            fit_file.to_file(modified_fit_file_path)

            self.logger.info(f"Modified FIT file saved to {modified_fit_file_path}")
            return modified_fit_file_path

        except Exception as e:
            raise RuntimeError(f"Failed to modify FIT file: {e}") from e

    def cleanup_file(self, file_path: str) -> None:
        """Clean up a temporary file.

        Args:
            file_path: Path to the file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Cleaned up file: {file_path}")
        except OSError as e:
            self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
