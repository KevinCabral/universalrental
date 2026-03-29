#!/usr/bin/env python3
"""
Test script to verify evaluation display in rental detail view
Usage: python test_evaluation_display.py
"""

import os
import sys
import django
from datetime import date, timedelta

# Add the project root to the Python path
sys.path.append('/home/kcabral/sga_v2')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.vehicle_rental.models import Vehicle, Customer, Rental, RentalEvaluation
from django.contrib.auth.models import User

def test_evaluation_display():
    """Test evaluation display in rental detail view"""
    print("🔍 Testing Evaluation Display in Rental Detail View")
    print("=" * 60)
    
    try:
        # Find completed rentals with evaluations
        completed_rentals = Rental.objects.filter(status='completed')
        rentals_with_evaluation = []
        rentals_without_evaluation = []
        
        for rental in completed_rentals:
            try:
                evaluation = rental.evaluation
                rentals_with_evaluation.append((rental, evaluation))
                print(f"✅ Rental #{rental.pk} - HAS evaluation (Rating: {evaluation.overall_rating}/5)")
            except RentalEvaluation.DoesNotExist:
                rentals_without_evaluation.append(rental)
                print(f"⚠️  Rental #{rental.pk} - NO evaluation")
        
        print(f"\n📊 Summary:")
        print(f"   • Completed rentals: {completed_rentals.count()}")
        print(f"   • With evaluations: {len(rentals_with_evaluation)}")
        print(f"   • Without evaluations: {len(rentals_without_evaluation)}")
        
        # Create a test evaluation if none exist
        if not rentals_with_evaluation and rentals_without_evaluation:
            print(f"\n🚧 Creating test evaluation for demonstration...")
            test_rental = rentals_without_evaluation[0]
            
            evaluation = RentalEvaluation.objects.create(
                rental=test_rental,
                overall_rating=4,
                vehicle_condition_rating=5,
                service_quality_rating=4,
                value_for_money_rating=3,
                would_recommend=True,
                comments="Excelente serviço! O veículo estava em ótimas condições.",
                had_issues=False
            )
            
            print(f"✅ Created test evaluation for rental #{test_rental.pk}")
            print(f"   • Overall Rating: {evaluation.overall_rating}/5")
            print(f"   • Would Recommend: {evaluation.would_recommend}")
            print(f"   • Comments: {evaluation.comments[:50]}...")
        
        # Display evaluation details for testing
        if rentals_with_evaluation or (not rentals_with_evaluation and rentals_without_evaluation):
            print(f"\n🎯 Test URLs to check:")
            
            # Show URLs for rentals with evaluations
            for rental, evaluation in rentals_with_evaluation:
                print(f"   📄 Rental #{rental.pk} (WITH evaluation):")
                print(f"      URL: /vehicle-rental/rentals/{rental.pk}/")
                print(f"      Rating: {evaluation.overall_rating}/5, Stars: {evaluation.rating_stars}")
                print(f"      Recommend: {'Yes' if evaluation.would_recommend else 'No'}")
                print()
            
            # Show URLs for rentals without evaluations
            for rental in rentals_without_evaluation[:3]:  # Show max 3
                print(f"   📄 Rental #{rental.pk} (WITHOUT evaluation):")
                print(f"      URL: /vehicle-rental/rentals/{rental.pk}/")
                print(f"      Should show: 'O cliente ainda não avaliou este aluguer.'")
                print()
        
        print("🎉 Evaluation display test completed!")
        print("\n💡 To test:")
        print("   1. Open any of the URLs above in your browser")
        print("   2. Look for the 'Avaliação do Cliente' card in the sidebar")
        print("   3. Verify star ratings, recommendations, and comments display correctly")
        
    except Exception as e:
        print(f"❌ Error during evaluation display test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evaluation_display()