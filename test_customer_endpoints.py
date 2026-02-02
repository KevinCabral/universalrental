#!/usr/bin/env python
"""
Test Customer API Endpoints with Authentication
"""
import requests
import json

BASE_URL = "http://localhost:8090/vehicle-rental/api/customer"

def test_complete_flow():
    print("\n" + "="*60)
    print("🚀 Testing Complete Customer API Flow")
    print("="*60)
    
    # Step 1: Login
    print("\n1️⃣  Testing Login...")
    login_data = {
        "email": "customer@example.com",  # Update with real customer
        "password": "password123"          # Update with real password
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data['token']
            print(f"   ✅ Login successful!")
            print(f"   Token: {token[:30]}...")
            print(f"   Customer: {data['customer']['first_name']} {data['customer']['last_name']}")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   Response: {response.json()}")
            return None
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server. Make sure Django is running:")
        print("   Run: python manage.py runserver 8090")
        return None
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None
    
    # Step 2: Test Rentals Endpoint
    print("\n2️⃣  Testing GET /rentals/ (with token)...")
    try:
        response = requests.get(
            f"{BASE_URL}/rentals/",
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            rentals = response.json()
            print(f"   ✅ Success! Found {len(rentals)} rental(s)")
            if rentals:
                print(f"   Sample rental: ID={rentals[0]['id']}, Status={rentals[0]['status']}")
        else:
            print(f"   ❌ Failed: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 3: Test Active Rentals
    print("\n3️⃣  Testing GET /rentals/active/ (with token)...")
    try:
        response = requests.get(
            f"{BASE_URL}/rentals/active/",
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            rentals = response.json()
            print(f"   ✅ Success! Found {len(rentals)} active rental(s)")
        else:
            print(f"   ❌ Failed: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 4: Test Rental History
    print("\n4️⃣  Testing GET /rentals/history/ (with token)...")
    try:
        response = requests.get(
            f"{BASE_URL}/rentals/history/",
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            rentals = response.json()
            print(f"   ✅ Success! Found {len(rentals)} historical rental(s)")
        else:
            print(f"   ❌ Failed: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 5: Test Vehicles Endpoint (public, no auth needed)
    print("\n5️⃣  Testing GET /vehicles/ (public endpoint)...")
    try:
        response = requests.get(
            f"{BASE_URL}/vehicles/",
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"   ✅ Success! Found {len(vehicles)} available vehicle(s)")
            if vehicles:
                v = vehicles[0]
                print(f"   Sample: {v.get('brand_name')} {v.get('model')} - €{v.get('daily_rate')}/day")
        elif response.status_code == 500:
            print(f"   ❌ Server Error (500)")
            print(f"   This might be due to missing data or serializer issues")
        else:
            print(f"   ❌ Failed: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 6: Test without authentication (should fail on protected endpoints)
    print("\n6️⃣  Testing /rentals/ WITHOUT token (should fail)...")
    try:
        response = requests.get(
            f"{BASE_URL}/rentals/",
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 401:
            print(f"   ✅ Correctly rejected: Authentication required")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ Test suite completed!")
    print("="*60 + "\n")
    
    return token


if __name__ == "__main__":
    print("\n" + "🧪 Customer API Authentication Test")
    print("="*60)
    print("\n⚠️  Before running:")
    print("   1. Start Django: python manage.py runserver 8090")
    print("   2. Update email/password in this script")
    print("   3. Ensure you have a customer account created")
    
    test_complete_flow()
