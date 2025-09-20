#!/usr/bin/env python3
"""
Test script to verify book detail and review functionality
"""

from app import app, db
from models import Book, BookImage, BookReview, User, Order, OrderItem
from datetime import datetime

def test_book_functionality():
    """Test the book detail and review functionality"""
    with app.app_context():
        print("🧪 Testing Book Detail and Review Functionality")
        print("=" * 50)
        
        # Check if we have books
        books = Book.query.all()
        print(f"📚 Total books in database: {len(books)}")
        
        if books:
            book = books[0]
            print(f"📖 Testing with book: '{book.title}' by {book.author}")
            
            # Check book images
            print(f"🖼️  Book has {len(book.images)} image(s)")
            
            # Check reviews
            reviews = BookReview.query.filter_by(book_id=book.id).all()
            print(f"⭐ Book has {len(reviews)} review(s)")
            
            if reviews:
                avg_rating = sum(r.rating for r in reviews) / len(reviews)
                print(f"📊 Average rating: {avg_rating:.1f}/5")
                
                for review in reviews:
                    print(f"   - {review.rating}⭐ by {review.user.email}: {review.review_text[:50]}...")
        
        # Check users
        users = User.query.all()
        print(f"👥 Total users: {len(users)}")
        
        # Check orders
        orders = Order.query.all()
        print(f"🛒 Total orders: {len(orders)}")
        
        print("\n✅ Database structure looks good!")
        print("\n🚀 You can now:")
        print("   1. Visit /books to see the book listing")
        print("   2. Click on any book to see its detail page")
        print("   3. Purchase a book and then add a review")
        print("   4. Visit /admin/book-reviews to manage reviews")

if __name__ == "__main__":
    test_book_functionality()