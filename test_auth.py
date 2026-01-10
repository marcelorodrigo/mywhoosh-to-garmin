#!/usr/bin/env python3
"""Quick test script to verify MyWhoosh authentication."""

import requests
import uuid
import json

def test_mywhoosh_auth():
    """Test MyWhoosh authentication endpoint."""
    
    # Note: Replace with actual credentials for testing
    payload = {
        "Username": "test@example.com",
        "Password": "test_password",
        "Platform": "Android",
        "Action": 1001,
        "CorrelationId": str(uuid.uuid4()),
        "DeviceId": str(uuid.uuid4()),
        "Authorization": ""
    }
    
    print("Testing MyWhoosh authentication endpoint...")
    print(f"URL: https://services.mywhoosh.com/http-service/api/login")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(
            "https://services.mywhoosh.com/http-service/api/login",
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("Success"):
                print("\n✓ Authentication successful!")
                print(f"WhooshId: {data.get('WhooshId')}")
                print(f"AccessToken: {data.get('AccessToken')[:50]}...")
            else:
                print(f"\n✗ Authentication failed: {data.get('Message')}")
        else:
            print(f"\n✗ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    test_mywhoosh_auth()
