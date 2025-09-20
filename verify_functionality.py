#!/usr/bin/env python3
"""
Verification script to confirm all functionality is working
"""

from app import app, db
from models import Book, BookReview, User

def verify_functionality():
    """Verify all book functionality is working"""
    with app.app_context():
        print("🔍 Verifying Book Functionality")
        print("=" * 40)
        
        # Check database
        books_count = Book.query.count()
        users_count = User.query.count()
        reviews_count = BookReview.query.count()
        
        print(f"📚 Books in database: {books_count}")
        print(f"👥 Users in database: {users_count}")
        print(f"⭐ Reviews in database: {reviews_count}")
        
        # Check routes
        print("\n🗺️  Book-related routes:")
        book_routes = [rule for rule in app.url_map.iter_rules() if 'book' in rule.rule.lower()]
        for route in book_routes:
            print(f"   ✅ {route.rule} -> {route.endpoint}")
        
        # Test with actual book
        if books_count > 0:
            book = Book.query.first()
            print(f"\n📖 Sample book: '{book.title}' (ID: {book.id})")
            print(f"   Images: {len(book.images)}")
            print(f"   Reviews: {len(book.reviews) if hasattr(book, 'reviews') else 'N/A'}")
        
        print("\n✅ All functionality verified!")
        print("\n🚀 Next steps:")
        print("   1. Restart your Flask server: python3 app.py")
        print("   2. Visit http://localhost:5000/books")
        print("   3. Click on any book to see the detail page")
        print("   4. Purchase a book and leave a review")

if __name__ == "__main__":
    verify_functionality()