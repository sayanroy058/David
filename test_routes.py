#!/usr/bin/env python3
"""
Test script to verify routes are working
"""

from app import app

def test_routes():
    """Test if the book_detail route is properly registered"""
    with app.test_client() as client:
        print("🧪 Testing Flask Routes")
        print("=" * 30)
        
        # Test books page
        print("📚 Testing /books route...")
        try:
            response = client.get('/books')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Books page loads successfully")
            else:
                print(f"   ❌ Books page failed with status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test book detail page
        print("\n📖 Testing /book/1 route...")
        try:
            response = client.get('/book/1')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Book detail page loads successfully")
            elif response.status_code == 404:
                print("   ⚠️  Book not found (expected if no book with ID 1)")
            else:
                print(f"   ❌ Book detail page failed with status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # List all routes
        print("\n🗺️  All registered routes:")
        for rule in app.url_map.iter_rules():
            if 'book' in rule.rule.lower():
                print(f"   {rule.rule} -> {rule.endpoint}")

if __name__ == "__main__":
    test_routes()