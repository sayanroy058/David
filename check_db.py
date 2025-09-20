from app import app, db
from models import HeroSlider

with app.app_context():
    slides = HeroSlider.query.all()
    print('\nHero Slides in Database:\n')
    for slide in slides:
        print(f'ID: {slide.id}, Title: {slide.title}, Button URL: {slide.button_url}')