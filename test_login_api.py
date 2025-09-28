#!/usr/bin/env python3
"""
MCP server test for login functionality
"""

import requests
import json

def test_login():
    """Test the login API endpoint directly"""

    base_url = "http://localhost:8002"

    # Test credentials
    login_data = {
        "email": "test@mealsplit.com",
        "password": "testpassword123"
    }

    print("🔐 Testing MealSplit Login API")
    print("=" * 40)
    print(f"Email: {login_data['email']}")
    print(f"Password: {login_data['password']}")
    print()

    try:
        # Make login request
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print("✅ Login Successful!")
            print(f"Access Token: {data['access_token'][:50]}...")
            print(f"Token Type: {data['token_type']}")
            print(f"Refresh Token: {data['refresh_token'][:50]}...")

            # Test authenticated endpoint
            print("\n🔍 Testing Authenticated Endpoint...")

            auth_headers = {
                "Authorization": f"Bearer {data['access_token']}",
                "Content-Type": "application/json"
            }

            me_response = requests.get(
                f"{base_url}/api/v1/auth/me",
                headers=auth_headers
            )

            if me_response.status_code == 200:
                user_data = me_response.json()
                print("✅ Authentication Working!")
                print(f"User ID: {user_data['id']}")
                print(f"Email: {user_data['email']}")
                print(f"Display Name: {user_data['display_name']}")
                print(f"Active: {user_data['is_active']}")
            else:
                print(f"❌ Auth test failed: {me_response.status_code}")
                print(me_response.text)

        else:
            print("❌ Login Failed!")
            print(f"Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error - Make sure backend is running on localhost:8002")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_login()