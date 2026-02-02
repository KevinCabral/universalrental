#!/usr/bin/env python
"""
Test script for the Rental Evaluation API
Run this after starting the Django server to test the evaluation endpoints
"""

import requests
import json

# API base URL - adjust as needed
BASE_URL = "http://localhost:8000/vehicle-rental/api"
EVALUATIONS_URL = f"{BASE_URL}/evaluations"
RENTALS_URL = f"{BASE_URL}/rentals"

def test_rental_evaluation_api():
    """Test the Rental Evaluation API endpoints"""
    print("Testing Rental Evaluation API")
    print("=" * 40)
    
    print("Available endpoints:")
    print(f"  GET {EVALUATIONS_URL}/                    - List all evaluations")
    print(f"  GET {EVALUATIONS_URL}/{{id}}/               - Get specific evaluation")
    print(f"  POST {EVALUATIONS_URL}/                   - Create new evaluation")
    print(f"  PUT {EVALUATIONS_URL}/{{id}}/               - Update evaluation")
    print(f"  PATCH {EVALUATIONS_URL}/{{id}}/             - Partial update evaluation")
    print(f"  DELETE {EVALUATIONS_URL}/{{id}}/            - Delete evaluation")
    print(f"  GET {EVALUATIONS_URL}/statistics/          - Get evaluation statistics")
    print(f"  POST {RENTALS_URL}/{{id}}/create_evaluation/ - Create evaluation for rental")
    print(f"  GET {RENTALS_URL}/{{id}}/can_evaluate/      - Check if rental can be evaluated")
    
    print("\n" + "="*40)
    print("1. Create evaluation for a completed rental:")
    print(f"   curl -X POST {EVALUATIONS_URL}/ \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print('            "rental": 1,')
    print('            "overall_rating": 5,')
    print('            "vehicle_condition_rating": 4,')
    print('            "service_quality_rating": 5,')
    print('            "value_for_money_rating": 4,')
    print('            "comments": "Excellent service! The vehicle was clean and well-maintained.",')
    print('            "would_recommend": true,')
    print('            "had_issues": false')
    print("        }'")
    
    print("\n2. Create evaluation via rental endpoint:")
    print(f"   curl -X POST {RENTALS_URL}/1/create_evaluation/ \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print('            "overall_rating": 4,')
    print('            "vehicle_condition_rating": 4,')
    print('            "service_quality_rating": 3,')
    print('            "value_for_money_rating": 4,')
    print('            "comments": "Good overall experience, minor delays in pickup.",')
    print('            "would_recommend": true,')
    print('            "had_issues": true,')
    print('            "issue_description": "Vehicle pickup was delayed by 30 minutes."')
    print("        }'")
    
    print("\n3. Check if rental can be evaluated:")
    print(f"   curl -X GET {RENTALS_URL}/1/can_evaluate/")
    
    print("\n4. Get all evaluations with filters:")
    print(f"   curl -X GET '{EVALUATIONS_URL}/?min_rating=4&would_recommend=true'")
    
    print("\n5. Get evaluations for specific rental:")
    print(f"   curl -X GET '{EVALUATIONS_URL}/?rental_id=1'")
    
    print("\n6. Get evaluations for specific customer:")
    print(f"   curl -X GET '{EVALUATIONS_URL}/?customer_id=1'")
    
    print("\n7. Get evaluations for specific vehicle:")
    print(f"   curl -X GET '{EVALUATIONS_URL}/?vehicle_id=1'")
    
    print("\n8. Get evaluation statistics:")
    print(f"   curl -X GET {EVALUATIONS_URL}/statistics/")
    
    print("\n" + "="*40)
    print("Expected evaluation response format:")
    print("{")
    print('    "id": 1,')
    print('    "rental": 1,')
    print('    "rental_info": {')
    print('        "id": 1,')
    print('        "start_date": "2024-01-15",')
    print('        "end_date": "2024-01-20",')
    print('        "actual_return_date": "2024-01-20",')
    print('        "total_amount": "250.00",')
    print('        "status": "completed"')
    print('    },')
    print('    "customer_info": {')
    print('        "id": 1,')
    print('        "full_name": "John Doe",')
    print('        "email": "john@example.com"')
    print('    },')
    print('    "vehicle_info": {')
    print('        "id": 1,')
    print('        "registration_number": "ABC-123",')
    print('        "brand": "Toyota",')
    print('        "model": "Corolla",')
    print('        "year": 2024')
    print('    },')
    print('    "overall_rating": 5,')
    print('    "vehicle_condition_rating": 4,')
    print('    "service_quality_rating": 5,')
    print('    "value_for_money_rating": 4,')
    print('    "average_rating": 4.5,')
    print('    "rating_stars": "★★★★★",')
    print('    "comments": "Excellent service!",')
    print('    "would_recommend": true,')
    print('    "had_issues": false,')
    print('    "issue_description": null,')
    print('    "created_at": "2024-01-21T10:30:00Z",')
    print('    "updated_at": "2024-01-21T10:30:00Z"')
    print("}")
    
    print("\n" + "="*40)
    print("Statistics endpoint response:")
    print("{")
    print('    "total_evaluations": 25,')
    print('    "average_overall_rating": 4.2,')
    print('    "average_vehicle_condition": 4.1,')
    print('    "average_service_quality": 4.3,')
    print('    "average_value_for_money": 4.0,')
    print('    "recommendation_percentage": 85.0,')
    print('    "issues_percentage": 15.0')
    print("}")
    
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/swagger/")
    
    print("\nNote: Make sure you have:")
    print("  1. A running Django server")
    print("  2. Completed rental records in the database")
    print("  3. Applied all migrations: python manage.py migrate")
    print("  4. Only completed rentals can be evaluated")

if __name__ == "__main__":
    test_rental_evaluation_api()