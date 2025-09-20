from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

def utc_now():
    """Return current UTC timestamp - consistent replacement for deprecated utc_now()"""
    return datetime.now(timezone.utc)

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
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    certificates = db.relationship('Certificate', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    customer = db.relationship('Customer', backref='user', uselist=False)

class Customer(db.Model):
    __tablename__ = 'customers'
    __table_args__ = (db.UniqueConstraint('user_id', name='uq_customers_user_id'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    street_address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

# Association table for Book-Category
book_categories = db.Table(
    'book_categories',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

# Association table for Book-SubCategory
book_subcategories = db.Table(
    'book_subcategories',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('subcategory_id', db.Integer, db.ForeignKey('subcategories.id'), primary_key=True)
)

# Association table for Bundle-Book
bundle_books = db.Table(
    'bundle_books',
    db.Column('bundle_id', db.Integer, db.ForeignKey('bundle_offers.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True)
)


class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quantity = db.Column(db.Integer, default=1)
    original_price = db.Column(db.Float, nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    avg_rating = db.Column(db.Float, default=0.0)   # Average rating out of 5
    review_count = db.Column(db.Integer, default=0) # Number of reviews
    is_deleted = db.Column(db.Boolean, default=False) # Soft delete flag
    deleted_at = db.Column(db.DateTime, nullable=True) # When the book was deleted

    # Relationship to multiple images
    images = db.relationship('BookImage', backref='book', cascade="all, delete-orphan")

    # Relationship to reviews (with cascade delete)
    reviews = db.relationship('BookReview', backref='book', cascade="all, delete-orphan")

    # Many-to-Many with categories
    categories = db.relationship(
        'Category',
        secondary=book_categories,
        backref=db.backref('books', lazy='dynamic')
    )

    # Many-to-Many with subcategories
    subcategories = db.relationship(
        'SubCategory',
        secondary=book_subcategories,
        backref=db.backref('books', lazy='dynamic')
    )


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    # One-to-Many: A category can have many subcategories
    subcategories = db.relationship(
        'SubCategory',
        backref='category',
        cascade="all, delete-orphan",
        lazy=True
    )


class SubCategory(db.Model):
    __tablename__ = 'subcategories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)


class BookImage(db.Model):
    __tablename__ = 'book_images'

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)

class BookReview(db.Model):
    __tablename__ = 'book_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    user = db.relationship('User', backref='reviews')

class BundleOffer(db.Model):
    __tablename__ = 'bundle_offers'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    mrp = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False, default='percentage')  # 'percentage' or 'fixed'
    discount_value = db.Column(db.Float, nullable=False, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Many-to-Many with books
    books = db.relationship(
        'Book',
        secondary=bundle_books,
        backref=db.backref('bundles', lazy='dynamic')
    )
    
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=utc_now)
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
    date_created = db.Column(db.DateTime, default=utc_now)
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
    created_at = db.Column(db.DateTime, default=utc_now)

class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    is_offline = db.Column(db.Boolean, default=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    course = db.relationship('Course', backref='certificates')

class UserCourse(db.Model):
    __tablename__ = 'user_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=utc_now)
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
    posted_on = db.Column(db.DateTime, default=utc_now)

    applications = db.relationship('JobApplication', backref='job', cascade="all, delete-orphan")


class JobApplication(db.Model):
    __tablename__ = 'job_applications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    resume = db.Column(db.String(255), nullable=False)  # File path to uploaded resume
    applied_on = db.Column(db.DateTime, default=utc_now)

    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    
class HeroSlider(db.Model):
    __tablename__ = 'hero_slider'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    button_text = db.Column(db.String(100), default='View Success Stories')
    button_url = db.Column(db.String(255), default='#')  # URL for the button
    image = db.Column(db.String(255))  # relative path for PC image, e.g., 'images/slider1.jpg'
    mobile_image = db.Column(db.String(255))  # relative path for mobile image, e.g., 'images/slider1_mobile.jpg'
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
class Testimonial(db.Model):
    __tablename__ = 'testimonials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=True)
    message = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)  # Path to student's image
    created_at = db.Column(db.DateTime, default=utc_now)
    

    
class FullOrderDetail(db.Model):
    __tablename__ = 'full_order_details'
    
    # DATA CONSISTENCY RULE: For bundle orders, item_id must equal bundle_id
    # For non-bundle orders, bundle_id must be NULL
    # Database CHECK constraint enforces: 
    # (item_type = 'bundle' AND bundle_id = item_id) OR (item_type != 'bundle' AND bundle_id IS NULL)

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle_offers.id'), nullable=True)

    custom_order_id = db.Column(db.String(30), nullable=True)  # <-- Added this line

    item_id = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # Supports 'book', 'course', 'bundle'
    item_title = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)

    full_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    order = db.relationship('Order', backref='full_order_details')
    transaction = db.relationship('Transaction', backref='full_order_details')
    customer = db.relationship('Customer', backref='orders')
    bundle = db.relationship('BundleOffer', backref='order_details')