#!/usr/bin/env python3
"""
Database migration script to add mobile_image column to hero_slider table
Run this script to update existing databases with the new mobile image functionality
"""

from flask import Flask
from models import db, HeroSlider
import os

def create_app():
    app = Flask(__name__)
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "site.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def update_database():
    app = create_app()
    
    with app.app_context():
        try:
            # Check if mobile_image column already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('hero_slider')]
            
            if 'mobile_image' not in columns:
                print("Adding mobile_image column to hero_slider table...")
                
                # Add the mobile_image column using text() for raw SQL
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE hero_slider ADD COLUMN mobile_image VARCHAR(255)'))
                    conn.commit()
                
                print("✅ Successfully added mobile_image column to hero_slider table")
                print("📱 You can now upload separate images for mobile and PC in the admin panel")
                print("🖥️  PC Image recommended size: 1920×620 pixels")
                print("📱 Mobile Image recommended size: 1440×630 pixels")
            else:
                print("✅ mobile_image column already exists in hero_slider table")
                
        except Exception as e:
            print(f"❌ Error updating database: {e}")
            return False
            
    return True

if __name__ == '__main__':
    print("🔄 Updating hero slider database schema...")
    if update_database():
        print("✅ Database update completed successfully!")
    else:
        print("❌ Database update failed!")