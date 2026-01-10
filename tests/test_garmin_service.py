import pytest
from services.garmin_service import GarminService

def test_garmin_service_init():
    svc = GarminService(username='user', password='pass')
    assert svc.username == 'user'
    assert svc.password == 'pass'
