from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_popular = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(255), nullable=True)  # Stores filename or file path
    price = db.Column(db.Float, nullable=False, default=0.0)
    is_certification = db.Column(db.Boolean, default=False)
    subject = db.Column(db.String(100), nullable=True)
    difficulty_level = db.Column(db.String(50), nullable=True)  # Beginner, Intermediate, Advanced
    duration = db.Column(db.String(50), nullable=True)  # e.g., "4 weeks", "2 months"
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)

class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(255), nullable=True)  # Stores filename or file path

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Relationships
    certificates = db.relationship('Certificate', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    original_price = db.Column(db.Float, nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)

    # Relationship to multiple images
    images = db.relationship('BookImage', backref='book', cascade="all, delete-orphan")


class BookImage(db.Model):
    __tablename__ = 'book_images'

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')
    total_amount = db.Column(db.Float, nullable=True)  # Store the total order amount including tax
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    
    # Relationship
    book = db.relationship('Book', backref='order_items')

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    
    # Relationship
    order = db.relationship('Order', backref='transactions')

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='certificates')

class UserCourse(db.Model):
    __tablename__ = 'user_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_status = db.Column(db.String(50), default='enrolled')  # enrolled, in-progress, completed
    
    # Relationships
    user = db.relationship('User', backref=db.backref('enrolled_courses', lazy=True))
    course = db.relationship('Course', backref=db.backref('enrolled_users', lazy=True))

class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('JobApplication', backref='job', cascade="all, delete-orphan")


class JobApplication(db.Model):
    __tablename__ = 'job_applications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    resume = db.Column(db.String(255), nullable=False)  # File path to uploaded resume
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)

    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    
class HeroSlider(db.Model):
    __tablename__ = 'hero_slider'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    button_text = db.Column(db.String(100), default='View Success Stories')
    image = db.Column(db.String(255))  # relative path, e.g., 'images/slider1.jpg'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Testimonial(db.Model):
    __tablename__ = 'testimonials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=True)
    message = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)  # Path to student's image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    subcategories = db.relationship('SubCategory', backref='category', cascade="all, delete-orphan", lazy=True)

class SubCategory(db.Model):
    __tablename__ = 'subcategories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)