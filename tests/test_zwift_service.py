import pytest
from services.zwift_service import ZwiftService

def test_zwift_service_init():
    svc = ZwiftService(username='user', password='pass')
    assert svc.username == 'user'
    assert svc.password == 'pass'
