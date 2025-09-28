"""
AB Testing Example Script
========================

This script demonstrates how to use the Social Suit AB testing functionality.
It shows how to create, monitor, and complete AB tests programmatically.
"""

import asyncio
import json
from datetime import datetime
from services.ab_testing.ab_test_service import (
    run_ab_test, get_test_details, get_user_tests, 
    update_test_metrics, complete_test
)
from services.ab_testing.cache_service import ABTestCacheService


async def create_sample_ab_test():
    """Create a sample AB test for button color optimization"""
    
    user_id = "demo_user_123"
    
    # Define the AB test configuration
    test_config = {
        "name": "Button Color Optimization",
        "description": "Testing different button colors to improve conversion rates",
        "variations": [
            {
                "name": "Control (Blue Button)",
                "content": {
                    "button_color": "#007bff",
                    "button_text": "Sign Up Now",
                    "button_style": "primary"
                }
            },
            {
                "name": "Variant A (Green Button)",
                "content": {
                    "button_color": "#28a745",
                    "button_text": "Sign Up Now",
                    "button_style": "success"
                }
            },
            {
                "name": "Variant B (Red Button)",
                "content": {
                    "button_color": "#dc3545",
                    "button_text": "Join Today!",
                    "button_style": "danger"
                }
            }
        ],
        "target_metric": "conversion_rate",
        "duration_days": 14,
        "traffic_split": 33  # Equal split between 3 variations
    }
    
    try:
        # Create the AB test
        print("🚀 Creating AB test...")
        test_result = await run_ab_test(user_id, test_config)
        
        print(f"✅ AB test created successfully!")
        print(f"   Test ID: {test_result['test_id']}")
        print(f"   Name: {test_result['name']}")
        print(f"   Status: {test_result['status']}")
        print(f"   Estimated completion: {test_result['estimated_completion_date']}")
        
        return test_result['test_id']
        
    except Exception as e:
        print(f"❌ Error creating AB test: {e}")
        return None


async def simulate_test_metrics(test_id, user_id):
    """Simulate updating test metrics over time"""
    
    print("\n📊 Simulating test metrics...")
    
    # Simulate metrics for each variation
    variations_metrics = [
        {
            "variation": "control",
            "metrics": {
                "impressions": 1000,
                "engagements": 150,
                "clicks": 80,
                "conversions": 25
            }
        },
        {
            "variation": "variant_a",
            "metrics": {
                "impressions": 1000,
                "engagements": 180,
                "clicks": 95,
                "conversions": 35
            }
        },
        {
            "variation": "variant_b",
            "metrics": {
                "impressions": 1000,
                "engagements": 120,
                "clicks": 65,
                "conversions": 20
            }
        }
    ]
    
    for variation_data in variations_metrics:
        try:
            await update_test_metrics(
                test_id, 
                user_id, 
                variation_data["variation"], 
                variation_data["metrics"]
            )
            
            conversion_rate = (variation_data["metrics"]["conversions"] / 
                             variation_data["metrics"]["impressions"]) * 100
            
            print(f"   ✅ {variation_data['variation']}: "
                  f"{variation_data['metrics']['conversions']} conversions "
                  f"({conversion_rate:.1f}% rate)")
            
        except Exception as e:
            print(f"   ❌ Error updating {variation_data['variation']}: {e}")


async def analyze_test_results(test_id, user_id):
    """Analyze and display test results"""
    
    print("\n📈 Analyzing test results...")
    
    try:
        # Get detailed test results
        test_details = await get_test_details(test_id, user_id)
        
        if test_details:
            print(f"   Test: {test_details['name']}")
            print(f"   Status: {test_details['status']}")
            
            # Display results for each variation
            for variation in test_details.get('variations', []):
                metrics = variation.get('metrics', {})
                if metrics.get('impressions', 0) > 0:
                    conversion_rate = (metrics.get('conversions', 0) / 
                                     metrics.get('impressions', 1)) * 100
                    
                    print(f"   📊 {variation['name']}:")
                    print(f"      - Impressions: {metrics.get('impressions', 0):,}")
                    print(f"      - Conversions: {metrics.get('conversions', 0):,}")
                    print(f"      - Conversion Rate: {conversion_rate:.2f}%")
        
        return test_details
        
    except Exception as e:
        print(f"   ❌ Error analyzing results: {e}")
        return None


async def complete_ab_test(test_id, user_id):
    """Complete the AB test and determine winner"""
    
    print("\n🏁 Completing AB test...")
    
    try:
        completion_result = await complete_test(test_id, user_id)
        
        print(f"   ✅ Test completed successfully!")
        print(f"   🏆 Winner: {completion_result.get('winner', 'No clear winner')}")
        print(f"   📅 Completed on: {completion_result.get('completion_date', 'Unknown')}")
        
        if 'winner_metrics' in completion_result:
            winner_metrics = completion_result['winner_metrics']
            print(f"   📊 Winner Performance:")
            print(f"      - Conversion Rate: {winner_metrics.get('conversion_rate', 0):.2f}%")
            print(f"      - Total Conversions: {winner_metrics.get('conversions', 0):,}")
        
        return completion_result
        
    except Exception as e:
        print(f"   ❌ Error completing test: {e}")
        return None


async def demonstrate_cache_functionality():
    """Demonstrate caching functionality"""
    
    print("\n🗄️  Demonstrating cache functionality...")
    
    user_id = "demo_user_123"
    
    try:
        # Get user tests (should use cache)
        user_tests = await ABTestCacheService.get_user_tests(user_id)
        print(f"   📋 Found {len(user_tests)} tests for user")
        
        # Get active tests (should use cache)
        active_tests = await ABTestCacheService.get_active_tests()
        print(f"   🔄 Found {len(active_tests)} active tests system-wide")
        
        # Demonstrate cache invalidation
        await ABTestCacheService.invalidate_user_test_cache(user_id)
        print(f"   🗑️  Invalidated cache for user {user_id}")
        
    except Exception as e:
        print(f"   ❌ Error with cache operations: {e}")


async def main():
    """Main demonstration function"""
    
    print("=" * 60)
    print("🧪 Social Suit AB Testing Demo")
    print("=" * 60)
    
    # Step 1: Create an AB test
    test_id = await create_sample_ab_test()
    
    if not test_id:
        print("❌ Failed to create AB test. Exiting demo.")
        return
    
    user_id = "demo_user_123"
    
    # Step 2: Simulate test metrics
    await simulate_test_metrics(test_id, user_id)
    
    # Step 3: Analyze results
    test_details = await analyze_test_results(test_id, user_id)
    
    # Step 4: Complete the test
    if test_details:
        completion_result = await complete_ab_test(test_id, user_id)
    
    # Step 5: Demonstrate cache functionality
    await demonstrate_cache_functionality()
    
    print("\n" + "=" * 60)
    print("✅ AB Testing Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())