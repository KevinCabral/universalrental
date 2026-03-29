"""
Test script for customer-facing API endpoints
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8090/vehicle-rental/api/customer"

def test_customer_registration():
    """Test customer registration endpoint"""
    print("\n=== Testing Customer Registration ===")
    
    customer_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": f"john.doe.{datetime.now().timestamp()}@example.com",  # Unique email
        "phone_number": "+351987654321",
        "address_line_1": "Rua Principal 123",
        "city": "Lisboa",
        "postal_code": "1000-001",
        "country": "Portugal",
        "id_number": f"PT{int(datetime.now().timestamp())}",
        "driving_license_number": f"DL{int(datetime.now().timestamp())}",
        "license_expiry_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "password": "SecurePass123",
        "password_confirm": "SecurePass123"
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=customer_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Customer registration successful!")
        return response.json()
    else:
        print("❌ Customer registration failed!")
        return None


def test_available_vehicles():
    """Test available vehicles endpoint"""
    print("\n=== Testing Available Vehicles ===")
    
    response = requests.get(f"{BASE_URL}/vehicles/")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        vehicles = response.json()
        print(f"Found {len(vehicles)} available vehicles")
        if vehicles:
            print(f"First vehicle: {vehicles[0].get('brand_name')} {vehicles[0].get('model')}")
        print("✅ Vehicle availability check successful!")
        return vehicles
    else:
        print("❌ Vehicle availability check failed!")
        print(f"Response: {response.text}")
        return None


def test_vehicle_availability_date_range():
    """Test vehicle availability for specific date range"""
    print("\n=== Testing Vehicle Availability with Date Range ===")
    
    start_date = datetime.now() + timedelta(days=1)
    end_date = datetime.now() + timedelta(days=3)
    
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
    
    response = requests.get(f"{BASE_URL}/vehicles/", params=params)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        vehicles = response.json()
        print(f"Found {len(vehicles)} available vehicles for {start_date.date()} to {end_date.date()}")
        print("✅ Date range filter successful!")
        return vehicles
    else:
        print("❌ Date range filter failed!")
        return None


def test_customer_profile(token=None):
    """Test getting customer profile (requires authentication)"""
    print("\n=== Testing Customer Profile ===")
    
    headers = {}
    if token:
        headers['Authorization'] = f'Token {token}'
    
    response = requests.get(f"{BASE_URL}/register/me/", headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Profile retrieval successful!")
    elif response.status_code == 401:
        print("⚠️ Authentication required (expected without token)")
    else:
        print("❌ Profile retrieval failed!")
        print(f"Response: {response.text}")


def test_customer_rentals(token=None):
    """Test getting customer rentals (requires authentication)"""
    print("\n=== Testing Customer Rentals ===")
    
    headers = {}
    if token:
        headers['Authorization'] = f'Token {token}'
    
    response = requests.get(f"{BASE_URL}/rentals/", headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        rentals = response.json()
        print(f"Found {len(rentals)} rentals")
        print("✅ Rentals retrieval successful!")
    elif response.status_code in [200, 401]:
        print("⚠️ Authentication required or no rentals found (expected)")
    else:
        print("❌ Rentals retrieval failed!")
        print(f"Response: {response.text}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Customer-Facing API Tests")
    print("=" * 60)
    
    # Test 1: Customer Registration
    registration_result = test_customer_registration()
    
    # Test 2: Available Vehicles (public endpoint)
    test_available_vehicles()
    
    # Test 3: Vehicle Availability with Date Range
    test_vehicle_availability_date_range()
    
    # Test 4: Customer Profile (requires auth)
    test_customer_profile()
    
    # Test 5: Customer Rentals (requires auth)
    test_customer_rentals()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
    
    print("\n📝 API Endpoints Summary:")
    print(f"  - POST   {BASE_URL}/register/ - Customer registration (public)")
    print(f"  - GET    {BASE_URL}/register/me/ - Get customer profile (auth required)")
    print(f"  - PATCH  {BASE_URL}/register/update_profile/ - Update profile (auth required)")
    print(f"  - GET    {BASE_URL}/vehicles/ - List available vehicles (public)")
    print(f"  - GET    {BASE_URL}/vehicles/{{id}}/ - Vehicle detail (public)")
    print(f"  - GET    {BASE_URL}/vehicles/{{id}}/availability/ - Check availability (public)")
    print(f"  - GET    {BASE_URL}/rentals/ - List customer rentals (auth required)")
    print(f"  - GET    {BASE_URL}/rentals/active/ - Active rentals (auth required)")
    print(f"  - GET    {BASE_URL}/rentals/history/ - Rental history (auth required)")
    print(f"  - POST   {BASE_URL}/rentals/{{id}}/cancel/ - Cancel rental (auth required)")
    print(f"  - GET    {BASE_URL}/evaluations/ - List evaluations (auth required)")
    print(f"  - POST   {BASE_URL}/evaluations/ - Create evaluation (auth required)")


if __name__ == "__main__":
    main()
