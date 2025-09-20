#!/usr/bin/env python3
"""
Database migration script to add BookReview table
Run this script to add the book review functionality to your existing database
"""

from app import app, db
from models import BookReview

def add_book_reviews_table():
    """Add the BookReview table to the database"""
    with app.app_context():
        try:
            # Create the BookReview table
            db.create_all()
            print("✅ BookReview table created successfully!")
            
            # Verify the table was created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'book_reviews' in tables:
                print("✅ Verified: book_reviews table exists in database")
                
                # Show table structure
                columns = inspector.get_columns('book_reviews')
                print("\n📋 Table structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
            else:
                print("❌ Error: book_reviews table was not created")
                
        except Exception as e:
            print(f"❌ Error creating BookReview table: {e}")

if __name__ == "__main__":
    print("🚀 Adding BookReview table to database...")
    add_book_reviews_table()
    print("\n✨ Migration completed!")