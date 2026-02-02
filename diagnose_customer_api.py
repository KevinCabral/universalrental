#!/usr/bin/env python
"""
Diagnostic script to check customer authentication and API issues
"""
import requests
import json

BASE_URL = "http://localhost:8090"

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return True
    except:
        return False


def test_customer_exists():
    """Check if we can create or find a test customer"""
    print("\n📝 Checking Customer Setup...")
    print("-" * 60)
    
    # Try to register a test customer
    test_data = {
        "first_name": "Test",
        "last_name": "Customer",
        "email": "testcustomer@example.com",
        "phone_number": "+351999888777",
        "address_line_1": "Test Address 123",
        "city": "Lisboa",
        "postal_code": "1000-001",
        "country": "Portugal",
        "id_number": "TEST123456",
        "driving_license_number": "DL123456",
        "license_expiry_date": "2026-12-31",
        "password": "testpass123",
        "password_confirm": "testpass123"
    }
    
    response = requests.post(
        f"{BASE_URL}/vehicle-rental/api/customer/register/",
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 201:
        print("✅ Test customer created successfully")
        return "testcustomer@example.com", "testpass123"
    elif response.status_code == 400:
        error = response.json()
        if 'email' in error and 'already exists' in str(error['email']):
            print("✅ Test customer already exists (using existing)")
            return "testcustomer@example.com", "testpass123"
        else:
            print(f"⚠️  Registration error: {error}")
            return None, None
    else:
        print(f"❌ Unexpected response: {response.status_code}")
        print(f"   {response.json()}")
        return None, None


def main():
    print("\n" + "="*60)
    print("🔍 Customer API Diagnostic Tool")
    print("="*60)
    
    # Check 1: Server running?
    print("\n1️⃣  Checking if Django server is running...")
    if not check_server():
        print("❌ Cannot connect to Django server!")
        print("   Please start it with: python manage.py runserver 8090")
        return
    print("✅ Server is running")
    
    # Check 2: Get or create test customer
    email, password = test_customer_exists()
    if not email:
        print("\n❌ Cannot proceed without a test customer")
        return
    
    # Check 3: Login
    print("\n2️⃣  Testing Login Endpoint...")
    print("-" * 60)
    response = requests.post(
        f"{BASE_URL}/vehicle-rental/api/customer/login/",
        json={"email": email, "password": password},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        token = data['token']
        print(f"✅ Login successful!")
        print(f"   Token: {token[:30]}...")
        print(f"   Customer ID: {data['customer']['id']}")
        print(f"   Is Customer: {data['user']['is_customer']}")
    else:
        print(f"❌ Login failed")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return
    
    # Check 4: Test authenticated endpoints
    print("\n3️⃣  Testing Authenticated Endpoints...")
    print("-" * 60)
    
    endpoints = [
        ('GET', '/vehicle-rental/api/customer/rentals/', 'Customer Rentals'),
        ('GET', '/vehicle-rental/api/customer/rentals/active/', 'Active Rentals'),
        ('GET', '/vehicle-rental/api/customer/rentals/history/', 'Rental History'),
    ]
    
    for method, endpoint, name in endpoints:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            }
        )
        
        status_icon = "✅" if response.status_code == 200 else "❌"
        print(f"{status_icon} {name}: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   └─ Returned {len(data)} item(s)")
        elif response.status_code == 401:
            print(f"   └─ Authentication failed (token not recognized)")
        elif response.status_code == 500:
            print(f"   └─ Server error - check Django logs")
        else:
            try:
                print(f"   └─ {response.json()}")
            except:
                print(f"   └─ {response.text[:100]}")
    
    # Check 5: Test public endpoints
    print("\n4️⃣  Testing Public Endpoints...")
    print("-" * 60)
    
    response = requests.get(
        f"{BASE_URL}/vehicle-rental/api/customer/vehicles/",
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Vehicles List: {response.status_code}")
    if response.status_code == 200:
        vehicles = response.json()
        print(f"✅ Success! Found {len(vehicles)} vehicle(s)")
        if vehicles:
            v = vehicles[0]
            print(f"   Sample: {v.get('brand_name', 'N/A')} {v.get('model', 'N/A')}")
    elif response.status_code == 500:
        print(f"❌ Server error (500)")
        print(f"   Check Django console for traceback")
        print(f"   Common causes:")
        print(f"   - Missing related objects (brand, photos)")
        print(f"   - Serializer field errors")
        print(f"   - Database query issues")
    else:
        print(f"❌ Failed with status {response.status_code}")
    
    # Check 6: Test without auth (should fail)
    print("\n5️⃣  Testing Authentication Requirement...")
    print("-" * 60)
    
    response = requests.get(
        f"{BASE_URL}/vehicle-rental/api/customer/rentals/",
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 401:
        print("✅ Correctly requires authentication (401 Unauthorized)")
    else:
        print(f"⚠️  Expected 401, got {response.status_code}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Summary")
    print("="*60)
    print(f"""
✅ Working:
   - Server is running
   - Customer login endpoint
   - Authentication token generation
   
⚠️  Check if empty:
   - Customer rentals might be empty (no rentals created yet)
   - Add test rentals via Django admin to test these endpoints
   
❌ If vehicles endpoint returns 500:
   - Check Django console for the full error
   - Ensure vehicles have proper brand relationships
   - Check if serializer is trying to access missing fields
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
