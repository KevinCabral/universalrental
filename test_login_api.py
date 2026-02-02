#!/usr/bin/env python
"""
Test script for Customer Login API
"""
import requests
import json

BASE_URL = "http://localhost:8090/vehicle-rental/api/customer"

def test_login():
    """Test customer login endpoint"""
    print("\n" + "="*60)
    print("Testing Customer Login API")
    print("="*60)
    
    # Test with a customer account (you'll need to create one first or use existing)
    login_data = {
        "email": "customer@example.com",  # Replace with actual customer email
        "password": "password123"          # Replace with actual password
    }
    
    print(f"\n1. Testing POST {BASE_URL}/login/")
    print(f"   Request body: {json.dumps(login_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Login successful!")
            print(f"   Token: {data['token'][:20]}...")
            print(f"   Customer: {data['customer']['first_name']} {data['customer']['last_name']}")
            print(f"   Email: {data['customer']['email']}")
            print(f"   Is Customer: {data['user']['is_customer']}")
            return data['token']
        else:
            print(f"   ❌ Login failed")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Make sure the Django server is running")
        print("   Run: python manage.py runserver 8090")
        return None
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_generic_token_auth():
    """Test generic DRF token authentication endpoint"""
    print("\n" + "="*60)
    print("Testing Generic Token Authentication API")
    print("="*60)
    
    login_data = {
        "username": "customer@example.com",  # Email is used as username
        "password": "password123"
    }
    
    print(f"\n2. Testing POST /api-token-auth/")
    print(f"   Request body: {json.dumps(login_data, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:8090/api-token-auth/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Token obtained successfully!")
            print(f"   Token: {data['token'][:20]}...")
            return data['token']
        else:
            print(f"   ❌ Token request failed")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def test_authenticated_request(token):
    """Test making an authenticated request with the token"""
    if not token:
        print("\n⚠️  Skipping authenticated request test (no token)")
        return
    
    print("\n" + "="*60)
    print("Testing Authenticated Request")
    print("="*60)
    
    print(f"\n3. Testing GET {BASE_URL}/register/me/")
    print(f"   Using token: {token[:20]}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/register/me/",
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Profile retrieved successfully!")
            print(f"   Customer ID: {data['id']}")
            print(f"   Name: {data['first_name']} {data['last_name']}")
            print(f"   Email: {data['email']}")
            print(f"   Phone: {data.get('phone_number', 'N/A')}")
            print(f"   Rental Count: {data.get('rental_count', 0)}")
            print(f"   Active Rentals: {data.get('active_rentals', 0)}")
        else:
            print(f"   ❌ Request failed")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")


def test_invalid_login():
    """Test login with invalid credentials"""
    print("\n" + "="*60)
    print("Testing Invalid Login Credentials")
    print("="*60)
    
    login_data = {
        "email": "wrong@example.com",
        "password": "wrongpassword"
    }
    
    print(f"\n4. Testing POST {BASE_URL}/login/ (with invalid credentials)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Correctly rejected invalid credentials")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")


if __name__ == "__main__":
    print("\n" + "🚀 Customer Login API Test Suite")
    print("="*60)
    print("\n⚠️  IMPORTANT: Before running this test:")
    print("   1. Make sure Django server is running: python manage.py runserver 8090")
    print("   2. Update the email/password in this script to match a real customer account")
    print("   3. Or create a test customer via the registration endpoint first")
    
    # Run tests
    token = test_login()
    test_generic_token_auth()
    test_authenticated_request(token)
    test_invalid_login()
    
    print("\n" + "="*60)
    print("✅ Test suite completed!")
    print("="*60 + "\n")
