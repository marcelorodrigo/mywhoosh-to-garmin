import pytest
from unittest.mock import MagicMock
from services.activity_processor import ActivityProcessor

def test_activity_processor_init():
    mock_mywhoosh = MagicMock()
    mock_fit_file = MagicMock()
    mock_garmin = MagicMock()
    
    ap = ActivityProcessor(mock_mywhoosh, mock_fit_file, mock_garmin)
    assert isinstance(ap, ActivityProcessor)
    assert ap.mywhoosh_service == mock_mywhoosh
    assert ap.fit_file_service == mock_fit_file
    assert ap.garmin_service == mock_garmin
