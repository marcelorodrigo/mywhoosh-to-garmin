import pytest
from services.mywhoosh_service import MyWhooshService

def test_mywhoosh_service_init():
    svc = MyWhooshService(email='test@example.com', password='secret')
    assert svc.email == 'test@example.com'
    assert svc.password == 'secret'
