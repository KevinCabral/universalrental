#!/usr/bin/env python
"""
Test script for the Vehicle API with description field
Run this after starting the Django server to test the Vehicle API with description field
"""

import requests
import json

# API base URL - adjust as needed
BASE_URL = "http://localhost:8000/vehicle-rental/api/vehicles"

def test_vehicle_api_with_description():
    """Test the Vehicle API to verify description field is included"""
    print("Testing Vehicle API with Description Field")
    print("=" * 50)
    
    print("Available endpoints:")
    print(f"  GET {BASE_URL}/           - List all vehicles")
    print(f"  GET {BASE_URL}/{{id}}/      - Get specific vehicle")
    print(f"  POST {BASE_URL}/          - Create new vehicle")
    print(f"  PUT {BASE_URL}/{{id}}/      - Update vehicle")
    print(f"  PATCH {BASE_URL}/{{id}}/    - Partial update vehicle")
    print(f"  DELETE {BASE_URL}/{{id}}/   - Delete vehicle")
    
    print("\nTo test the API with description field:")
    print("\n1. Get all vehicles (check if description field is included):")
    print(f"   curl -X GET {BASE_URL}/")
    
    print("\n2. Get specific vehicle (check description field):")
    print(f"   curl -X GET {BASE_URL}/1/")
    
    print("\n3. Create vehicle with description (JSON):")
    print(f"   curl -X POST {BASE_URL}/ \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print('            "brand": 1,')
    print('            "model": "Test Car",')
    print('            "year": 2024,')
    print('            "description": "This is a test vehicle with additional features and notes.",')
    print('            "chassis_number": "TEST123456",')
    print('            "registration_number": "TEST-001",')
    print('            "color": "Blue",')
    print('            "fuel_type": "gasoline",')
    print('            "gearbox_type": "manual",')
    print('            "daily_rate": "50.00"')
    print("        }'")
    
    print("\n4. Update vehicle description only:")
    print(f"   curl -X PATCH {BASE_URL}/1/ \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print('            "description": "Updated description with more details about the vehicle condition and features."')
    print("        }'")
    
    print("\n5. Create vehicle with photo AND description (multipart/form-data):")
    print(f"   curl -X POST {BASE_URL}/ \\")
    print("        -F 'brand=1' \\")
    print("        -F 'model=Luxury Car' \\")
    print("        -F 'year=2024' \\")
    print("        -F 'description=Premium vehicle with leather seats, sunroof, and GPS navigation' \\")
    print("        -F 'chassis_number=LUX123456' \\")
    print("        -F 'registration_number=LUX-001' \\")
    print("        -F 'color=Black' \\")
    print("        -F 'fuel_type=gasoline' \\")
    print("        -F 'gearbox_type=automatic' \\")
    print("        -F 'daily_rate=80.00' \\")
    print("        -F 'photo=@/path/to/vehicle/photo.jpg'")
    
    print("\nExpected response now includes:")
    print("  - description: Text field with vehicle description")
    print("  - description will be null if not provided")
    print("  - description supports long text with line breaks")
    
    print("\nSample API Response:")
    print("{")
    print('  "id": 1,')
    print('  "brand": 1,')
    print('  "brand_name": "Toyota",')
    print('  "model": "Corolla",')
    print('  "year": 2024,')
    print('  "description": "Well-maintained vehicle with recent maintenance. Perfect for city driving.",')
    print('  "chassis_number": "JTD123456789",')
    print('  "registration_number": "ABC-123",')
    print('  "color": "White",')
    print('  "photo": "/media/vehicle_photos/1/vehicle_image.jpg",')
    print('  "daily_rate": "50.00",')
    print('  // ... other fields')
    print("}")
    
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/swagger/")
    
    print("\nNote: Make sure you have:")
    print("  1. A running Django server")
    print("  2. Applied database migrations: python manage.py migrate")
    print("  3. Valid vehicle brand records in the database")

if __name__ == "__main__":
    test_vehicle_api_with_description()