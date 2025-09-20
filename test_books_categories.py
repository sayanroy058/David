#!/usr/bin/env python3
"""
Test script to verify books categorization functionality
"""

from flask import Flask
from models import db, Book
import os

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "site.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def test_book_categories():
    app = create_app()
    
    with app.app_context():
        try:
            # Get all books
            books = Book.query.all()
            print(f"📚 Total books in database: {len(books)}")
            
            if not books:
                print("⚠️  No books found in database")
                return
            
            # Group books by category
            books_by_category = {}
            for book in books:
                category = book.category or 'Uncategorized'
                if category not in books_by_category:
                    books_by_category[category] = []
                books_by_category[category].append(book)
            
            print(f"\n📂 Books organized by categories:")
            print("=" * 50)
            
            for category, category_books in books_by_category.items():
                print(f"\n📖 {category}: {len(category_books)} book(s)")
                for book in category_books[:3]:  # Show first 3 books
                    print(f"   • {book.title} by {book.author}")
                if len(category_books) > 3:
                    print(f"   ... and {len(category_books) - 3} more")
            
            # Get distinct categories and subjects
            categories = [c[0] for c in db.session.query(Book.category).distinct().all() if c[0]]
            subjects = [s[0] for s in db.session.query(Book.subject).distinct().all() if s[0]]
            
            print(f"\n🏷️  Available categories: {categories}")
            print(f"📚 Available subjects: {subjects}")
            
            print(f"\n✅ Books categorization test completed successfully!")
            print(f"📊 Summary:")
            print(f"   • Total books: {len(books)}")
            print(f"   • Categories: {len(books_by_category)}")
            print(f"   • Distinct categories: {len(categories)}")
            print(f"   • Distinct subjects: {len(subjects)}")
            
        except Exception as e:
            print(f"❌ Error testing book categories: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Testing books categorization functionality...")
    test_book_categories()