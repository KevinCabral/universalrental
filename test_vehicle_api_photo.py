#!/usr/bin/env python
"""
Test script for the Vehicle API with photo field
Run this after starting the Django server to test the Vehicle API with photo field
"""

import requests
import json

# API base URL - adjust as needed
BASE_URL = "http://localhost:8000/vehicle-rental/api/vehicles"

def test_vehicle_api_with_photo():
    """Test the Vehicle API to verify photo field is included"""
    print("Testing Vehicle API with Photo Field")
    print("=" * 45)
    
    print("Available endpoints:")
    print(f"  GET {BASE_URL}/           - List all vehicles")
    print(f"  GET {BASE_URL}/{{id}}/      - Get specific vehicle")
    print(f"  POST {BASE_URL}/          - Create new vehicle")
    print(f"  PUT {BASE_URL}/{{id}}/      - Update vehicle")
    print(f"  PATCH {BASE_URL}/{{id}}/    - Partial update vehicle")
    print(f"  DELETE {BASE_URL}/{{id}}/   - Delete vehicle")
    
    print("\nTo test the API with photo field:")
    print("\n1. Get all vehicles (check if photo field is included):")
    print(f"   curl -X GET {BASE_URL}/")
    
    print("\n2. Get specific vehicle (check photo field):")
    print(f"   curl -X GET {BASE_URL}/1/")
    
    print("\n3. Create vehicle with photo (multipart/form-data):")
    print(f"   curl -X POST {BASE_URL}/ \\")
    print("        -F 'brand=1' \\")
    print("        -F 'model=Test Car' \\")
    print("        -F 'year=2024' \\")
    print("        -F 'chassis_number=TEST123456' \\")
    print("        -F 'registration_number=TEST-001' \\")
    print("        -F 'color=Blue' \\")
    print("        -F 'fuel_type=gasoline' \\")
    print("        -F 'gearbox_type=manual' \\")
    print("        -F 'daily_rate=50.00' \\")
    print("        -F 'photo=@/path/to/vehicle/photo.jpg'")
    
    print("\n4. Update vehicle photo:")
    print(f"   curl -X PATCH {BASE_URL}/1/ \\")
    print("        -F 'photo=@/path/to/new/photo.jpg'")
    
    print("\nExpected response now includes:")
    print("  - photo: URL to the uploaded image file")
    print("  - photo will be null if no image is uploaded")
    print("  - photo URLs will be relative (e.g., '/media/vehicle_photos/1/image.jpg')")
    
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/swagger/")
    
    print("\nNote: Make sure you have:")
    print("  1. A running Django server")
    print("  2. MEDIA_URL and MEDIA_ROOT properly configured")
    print("  3. File upload permissions set correctly")
    print("  4. Valid image files for testing")

if __name__ == "__main__":
    test_vehicle_api_with_photo()