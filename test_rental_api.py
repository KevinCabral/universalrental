#!/usr/bin/env python
"""
Test script for the new rental API endpoints
Run this after starting the Django server to test the new API endpoints
"""

import requests
import json
from datetime import datetime, date

# API base URL - adjust as needed
BASE_URL = "http://localhost:8000/vehicle-rental/api/rentals"

def test_rental_api_endpoints():
    """Test the new rental API endpoints"""
    print("Testing Rental API Endpoints")
    print("=" * 40)
    
    # You'll need to replace this with an actual rental ID from your database
    rental_id = 1
    
    # Test endpoints
    endpoints = {
        'confirm': f"{BASE_URL}/{rental_id}/confirm/",
        'cancel': f"{BASE_URL}/{rental_id}/cancel/", 
        'return': f"{BASE_URL}/{rental_id}/return_rental/"
    }
    
    print("Available endpoints:")
    for action, url in endpoints.items():
        print(f"  {action.upper()}: POST {url}")
    
    print("\nTo test these endpoints manually:")
    print("\n1. Confirm a rental:")
    print(f"   curl -X POST {endpoints['confirm']}")
    
    print("\n2. Cancel a rental:")
    print(f"   curl -X POST {endpoints['cancel']}")
    
    print("\n3. Return a rental:")
    print(f"   curl -X POST {endpoints['return']} \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print("            \"actual_return_date\": \"2024-01-15\",")
    print("            \"odometer_end\": 50000,")
    print("            \"fuel_level_end\": \"full\",")
    print("            \"damage_description\": \"Minor scratch on door\",")
    print("            \"damage_fee\": 100.00")
    print("        }'")
    
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/swagger/")
    
    print("\nNote: Make sure you have:")
    print("  1. A running Django server")
    print("  2. Valid rental records in the database")
    print("  3. Proper authentication if required")

if __name__ == "__main__":
    test_rental_api_endpoints()