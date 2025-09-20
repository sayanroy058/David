#!/usr/bin/env python3
"""
Verification script to check if the banner update was successful
"""

from flask import Flask
from models import db, HeroSlider
import os

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "site.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def verify_update():
    app = create_app()
    
    with app.app_context():
        try:
            # Check database schema
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('hero_slider')]
            
            print("🔍 Checking hero_slider table schema...")
            print(f"📋 Columns found: {columns}")
            
            # Verify required columns exist
            required_columns = ['id', 'title', 'description', 'button_text', 'button_url', 'image', 'mobile_image', 'updated_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All required columns present")
            
            # Test model functionality
            print("\n🧪 Testing HeroSlider model...")
            
            # Try to query existing slides
            slides = HeroSlider.query.all()
            print(f"📊 Found {len(slides)} existing slides")
            
            # Test model attributes
            test_slide = HeroSlider(
                title="Test Slide",
                description="Test Description",
                button_text="Test Button",
                button_url="#",
                image="test.jpg",
                mobile_image="test_mobile.jpg"
            )
            
            print("✅ HeroSlider model can be instantiated with mobile_image")
            
            # Check if we can access mobile_image attribute
            mobile_img = test_slide.mobile_image
            print(f"✅ mobile_image attribute accessible: {mobile_img}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            return False

def verify_files():
    print("\n📁 Checking file modifications...")
    
    files_to_check = [
        'models.py',
        'forms.py', 
        'app.py',
        'templates/admin_hero_slider.html',
        'templates/index.html'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Verifying banner responsive update...")
    
    db_ok = verify_update()
    files_ok = verify_files()
    
    if db_ok and files_ok:
        print("\n🎉 Banner responsive update verification PASSED!")
        print("📱 You can now use separate images for mobile and PC")
        print("🖥️  Access admin panel at: /admin/hero-slider")
    else:
        print("\n❌ Banner responsive update verification FAILED!")
        print("Please check the errors above and re-run the update.")