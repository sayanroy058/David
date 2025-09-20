#!/usr/bin/env python3
"""
Debug template rendering issue
"""

from app import app, db
from models import Book

def debug_template():
    """Debug the template rendering issue"""
    with app.test_client() as client:
        with app.app_context():
            print("🔍 Debugging Template Issue")
            print("=" * 30)
            
            # Check if we have books
            books = Book.query.limit(3).all()
            print(f"📚 Found {len(books)} books in database")
            
            if books:
                book = books[0]
                print(f"📖 First book: ID={book.id}, Title='{book.title}'")
                
                # Test url_for in app context
                try:
                    from flask import url_for
                    with client.session_transaction() as sess:
                        # Create a fake request context
                        pass
                    
                    # Try to render just the problematic part
                    print("🧪 Testing template rendering...")
                    
                    # Make a request to books page and capture any errors
                    response = client.get('/books')
                    print(f"📄 Response status: {response.status_code}")
                    
                    if response.status_code != 200:
                        print(f"❌ Error in response: {response.data.decode()[:500]}...")
                    else:
                        print("✅ Books page rendered successfully")
                        
                        # Check if the response contains the book detail links
                        response_text = response.data.decode()
                        if f'/book/{book.id}' in response_text:
                            print("✅ Book detail links found in response")
                        else:
                            print("❌ Book detail links not found in response")
                            
                except Exception as e:
                    print(f"❌ Template error: {e}")
            else:
                print("❌ No books found in database")

if __name__ == "__main__":
    debug_template()