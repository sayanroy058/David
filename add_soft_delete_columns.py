#!/usr/bin/env python3
"""
Database migration script to add soft delete columns to books table
Run this script to add is_deleted and deleted_at columns to existing books
"""

from app import app
from models import db, Book
from sqlalchemy import text

def add_soft_delete_columns():
    """Add is_deleted and deleted_at columns to books table"""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('books')]
            
            if 'is_deleted' not in columns:
                print("Adding is_deleted column to books table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE books ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                print("✅ is_deleted column added successfully")
            else:
                print("ℹ️  is_deleted column already exists")
            
            if 'deleted_at' not in columns:
                print("Adding deleted_at column to books table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE books ADD COLUMN deleted_at DATETIME'))
                    conn.commit()
                print("✅ deleted_at column added successfully")
            else:
                print("ℹ️  deleted_at column already exists")
            
            # Update existing books to set is_deleted = False if NULL
            print("Updating existing books to set is_deleted = False...")
            with db.engine.connect() as conn:
                conn.execute(text('UPDATE books SET is_deleted = FALSE WHERE is_deleted IS NULL'))
                conn.commit()
            print("✅ Existing books updated successfully")
            
            print("\n🎉 Database migration completed successfully!")
            print("All books are now ready for soft delete functionality.")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            print("Please check your database connection and try again.")

if __name__ == '__main__':
    print("🔄 Starting database migration for soft delete functionality...")
    print("=" * 60)
    add_soft_delete_columns()
