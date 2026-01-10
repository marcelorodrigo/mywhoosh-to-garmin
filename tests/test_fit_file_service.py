import pytest
from services.fit_file_service import FitFileService

def test_fit_file_service_init():
    fs = FitFileService()
    assert isinstance(fs, FitFileService)
