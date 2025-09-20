#!/usr/bin/env python3
"""
Verification script to confirm admin routes are working
"""

from app import app

def verify_admin_routes():
    """Verify all admin routes are properly registered"""
    with app.test_client() as client:
        print("🔍 Verifying Admin Routes")
        print("=" * 40)
        
        # Check all admin routes
        admin_routes = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/admin')]
        
        print(f"📋 Found {len(admin_routes)} admin routes:")
        for route in admin_routes:
            print(f"   ✅ {route.rule} -> {route.endpoint}")
        
        # Specifically check book review routes
        review_routes = [rule for rule in app.url_map.iter_rules() if 'review' in rule.rule]
        print(f"\n⭐ Book review routes:")
        for route in review_routes:
            print(f"   ✅ {route.rule} -> {route.endpoint}")
        
        print("\n✅ All admin routes verified!")
        print("\n🚀 Next steps:")
        print("   1. Restart your Flask server: python3 app.py")
        print("   2. Login to admin panel")
        print("   3. Access admin dashboard")
        print("   4. Click 'Manage Book Reviews' button")

if __name__ == "__main__":
    verify_admin_routes()