from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_from_directory, abort, current_app
from models import Book, BookImage, BookReview, Category, Customer, FullOrderDetail, HeroSlider, Job, JobApplication, SubCategory, Testimonial, db, Course, Teacher, User, Order, OrderItem, Transaction, Certificate, UserCourse, BundleOffer
from modelss.data import get_courses, get_books, get_certifications 
from admin_routes import admin_bp, admin_login_required
from forms import BookForm, BookReviewForm, CategoryForm, CustomerForm, HeroSliderForm, JobApplicationForm, JobForm, RegistrationForm, LoginForm, SubCategoryForm, TestimonialForm, ForgotPasswordForm, ResetPasswordForm
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import re
import razorpay
from datetime import datetime, timedelta, timezone
# For Python versions before 3.11, we'll use timezone.utc instead of datetime.UTC
from werkzeug.utils import secure_filename
from utils import generate_otp, send_reset_email

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Razorpay configuration
app.config['RAZORPAY_KEY_ID'] = 'rzp_live_83IOlByr8u0xkh'
app.config['RAZORPAY_KEY_SECRET'] = 'wul7YdoOtxjn0bTLnQZErnCY'
razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))

# Initialize DB
db.init_app(app)

# Add custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML line breaks"""
    if text:
        return text.replace('\n', '<br>')
    return text

# Register Blueprints
app.register_blueprint(admin_bp)

# User login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect('/login')  # Adjust this if your login route is different
        return f(*args, **kwargs)
    return decorated_function

# Helper Functions
def get_or_create_customer(user_id, customer_info):
    """Get existing customer or create new one with detailed address information"""
    try:
        # Check if customer already exists for this user
        customer = Customer.query.filter_by(user_id=user_id).first()
        
        if customer:
            # Update existing customer with new information
            customer.full_name = customer_info.get('full_name', customer.full_name)
            customer.email = customer_info.get('email', customer.email)
            customer.phone = customer_info.get('phone', customer.phone)
            customer.street_address = customer_info.get('street_address', customer.street_address)
            customer.city = customer_info.get('city', customer.city)
            customer.state = customer_info.get('state', customer.state)
            customer.pincode = customer_info.get('pincode', customer.pincode)
            customer.updated_at = datetime.now(timezone.utc)
        else:
            # Create new customer
            customer = Customer(
                user_id=user_id,
                full_name=customer_info.get('full_name', ''),
                email=customer_info.get('email', ''),
                phone=customer_info.get('phone', ''),
                street_address=customer_info.get('street_address', ''),
                city=customer_info.get('city', ''),
                state=customer_info.get('state', ''),
                pincode=customer_info.get('pincode', '')
            )
            db.session.add(customer)
        
        db.session.commit()
        return customer
        
    except Exception as e:
        db.session.rollback()
        print(f"Error managing customer: {e}")
        return None

# Routes
@app.route('/')
def index():
    courses = Course.query.filter_by(is_popular=True).all()
    all_books = Book.query.filter_by(is_deleted=False).all()
    teachers = Teacher.query.all()
    hero_slides = HeroSlider.query.order_by(HeroSlider.updated_at.desc()).all()
    testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('index.html', courses=courses, teachers=teachers, hero_slides=hero_slides, books=all_books, testimonials=testimonials)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(email=form.email.data, phone=form.phone.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            # Store user data in session
            session['user_id'] = user.id
            session['email'] = user.email
            session['phone'] = user.phone
            flash('Login successful.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate OTP
            otp = generate_otp()
            # Save OTP as reset token
            user.reset_token = otp
            # Using datetime.now(timezone.utc) instead of deprecated datetime.utcnow()
            user.reset_token_expiration = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.session.commit()
            
            # Send email with OTP
            if send_reset_email(user.email, otp):
                # Check if we're in test mode (email sending disabled)
                from utils import ENABLE_EMAIL_SENDING
                if not ENABLE_EMAIL_SENDING:
                    flash(f'TEST MODE: Your OTP is {otp}. In production, this would be sent via email.', 'info')
                else:
                    flash('Password reset OTP has been sent to your email.', 'success')
                return redirect(url_for('reset_password', email=user.email))
            else:
                flash('Failed to send email. Please try again.', 'danger')
        else:
            # Don't reveal that the user doesn't exist
            flash('If your email is registered, you will receive a password reset OTP.', 'info')
    return render_template('forgot_password.html', form=form)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    email = request.args.get('email', '')
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=request.form.get('email')).first()
        # Make sure we can compare the datetimes by making both timezone-aware
        valid_token = False
        if user and user.reset_token == form.otp.data and user.reset_token_expiration:
            # Convert naive datetime to aware datetime if needed
            expiration = user.reset_token_expiration
            if expiration.tzinfo is None:
                # If the stored datetime is naive, assume it's in UTC
                expiration = expiration.replace(tzinfo=timezone.utc)
            valid_token = expiration > datetime.now(timezone.utc)
            
        if user and user.reset_token == form.otp.data and valid_token:
            # Reset password
            user.password_hash = generate_password_hash(form.password.data)
            user.reset_token = None
            user.reset_token_expiration = None
            db.session.commit()
            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
    
    return render_template('reset_password.html', form=form, email=email)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('You must be logged in to view your profile.', 'warning')
        return redirect(url_for('login'))
    
    # Get user data
    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    
    # Get user courses
    user_courses = []
    user_course_enrollments = UserCourse.query.filter_by(user_id=user.id).all()
    
    for enrollment in user_course_enrollments:
        course = db.session.get(Course, enrollment.course_id)
        if course:
            # Get certificate if exists
            certificate = Certificate.query.filter_by(user_id=user.id, course_id=course.id).first()
            
            # Add course data
            course_data = {
                'id': course.id,
                'title': course.title,
                'image': course.image,
                'teacher': db.session.get(Teacher, course.teacher_id) if course.teacher_id else None,
                'enrollment_date': enrollment.enrollment_date.strftime('%Y-%m-%d') if enrollment.enrollment_date else 'N/A',
                'certificate': certificate
            }
            user_courses.append(course_data)
    
    # Get certificates
    certificates = Certificate.query.filter_by(user_id=user.id).all()
    
    # Get orders
    orders = []
    user_orders = Order.query.filter_by(user_id=user.id).all()
    for order in user_orders:
        transaction = Transaction.query.filter_by(order_id=order.id).first()
        order_data = {
            'id': order.id,
            'date': order.date_created.strftime('%Y-%m-%d') if order.date_created else 'N/A',
            'amount': transaction.amount if transaction else 0,
            'status': 'Completed' if transaction and transaction.status == 'completed' else 'Processing'
        }
        orders.append(order_data)
    
    return render_template('profile.html', 
                           user=user, 
                           user_courses=user_courses,
                           certificates=certificates,
                           orders=orders)

@app.route('/courses')
def courses():
    course_list = get_courses()
    return render_template('courses.html', courses=course_list)

@app.route('/books')
def books():
    query = Book.query.filter_by(is_deleted=False)

    title = request.args.get('title')
    author = request.args.get('author')
    category = request.args.get('category')
    subcategory = request.args.get('subject')   # subject = subcategory filter
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    view_type = request.args.get('view', 'category')  # 'category' or 'list'

    # Apply filters
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if category:
        query = query.join(Book.categories).filter(Category.name.ilike(f"%{category}%"))
    if subcategory:
        query = query.join(Book.subcategories).filter(SubCategory.name.ilike(f"%{subcategory}%"))
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    if max_price is not None:
        query = query.filter(Book.price <= max_price)

    books = query.all()
    
    # Distinct category and subcategory names for filters
    categories = [c[0] for c in db.session.query(Category.name).distinct().all() if c[0]]
    subjects = [s[0] for s in db.session.query(SubCategory.name).distinct().all() if s[0]]
    
    # Group books by category for category view
    books_by_category = {}
    if view_type == 'category':
        for book in books:
            if book.categories:
                for cat in book.categories:
                    if cat.name not in books_by_category:
                        books_by_category[cat.name] = []
                    books_by_category[cat.name].append(book)
            else:
                books_by_category.setdefault('Uncategorized', []).append(book)
        
        # Sort categories alphabetically, but put 'Uncategorized' last
        sorted_categories = sorted([cat for cat in books_by_category if cat != 'Uncategorized'])
        if 'Uncategorized' in books_by_category:
            sorted_categories.append('Uncategorized')
        
        books_by_category = {cat: books_by_category[cat] for cat in sorted_categories}

    return render_template(
        'books_new.html',
        books=books,
        books_by_category=books_by_category,
        categories=categories,
        subjects=subjects,
        view_type=view_type
    )


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    # Get all reviews for this book
    reviews = BookReview.query.filter_by(book_id=book_id).order_by(BookReview.created_at.desc()).all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
    
    # Check if current user has purchased this book
    user_purchased = False
    user_can_review = False
    user_existing_review = None
    
    if 'user_id' in session:
        user_id = session['user_id']
        user_order = db.session.query(OrderItem).join(Order).filter(
            Order.user_id == user_id,
            OrderItem.book_id == book_id,
            Order.status == 'completed'
        ).first()
        
        if user_order:
            user_purchased = True
            # Check if user already reviewed this book
            user_existing_review = BookReview.query.filter_by(
                book_id=book_id, 
                user_id=user_id
            ).first()
            
            if not user_existing_review:
                user_can_review = True
    
    # Get related books (any book sharing at least one category)
    related_books = []
    if book.categories:
        related_books = (
            Book.query.filter_by(is_deleted=False).join(Book.categories)
            .filter(Category.id.in_([c.id for c in book.categories]))
            .filter(Book.id != book_id)
            .limit(4)
            .all()
        )
    
    # Get active bundle offers that contain this book
    bundle_offers = BundleOffer.query.filter(
        BundleOffer.is_active == True,
        BundleOffer.books.any(id=book_id)
    ).all()
    
    # Calculate bundle savings for each bundle
    bundle_offers_with_savings = []
    for bundle in bundle_offers:
        savings_data = calculate_bundle_savings(bundle)
        bundle_offers_with_savings.append({
            'bundle': bundle,
            'total_mrp': savings_data['total_mrp'],
            'savings_amount': savings_data['savings_amount'],
            'savings_percentage': savings_data['savings_percentage']
        })
    
    return render_template(
        'book_detail.html',
        book=book,
        reviews=reviews,
        avg_rating=avg_rating,
        user_purchased=user_purchased,
        user_can_review=user_can_review,
        user_existing_review=user_existing_review,
        related_books=related_books,
        bundle_offers=bundle_offers_with_savings
    )


def calculate_bundle_savings(bundle):
    """Calculate bundle savings and return structured data"""
    try:
        # total MRP from books (prefer original_price)
        total_mrp = sum((getattr(b, 'original_price', None) or getattr(b, 'price', 0) or 0) for b in bundle.books)
        if total_mrp <= 0:
            return {"total_mrp": 0, "savings_amount": 0, "savings_percentage": 0}

        savings_amount = max(0, total_mrp - bundle.selling_price)
        savings_percentage = (savings_amount / total_mrp) * 100 if total_mrp > 0 else 0
        return {"total_mrp": total_mrp, "savings_amount": savings_amount, "savings_percentage": savings_percentage}
        
    except Exception as e:
        # Log error and return safe defaults
        current_app.logger.error(f"Error calculating bundle savings for bundle {bundle.id}: {str(e)}")
        return {
            'total_mrp': 0,
            'savings_amount': 0,
            'savings_percentage': 0
        }


@app.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def add_book_review(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    user_id = session['user_id']
    
    # Ensure user purchased the book
    user_order = db.session.query(OrderItem).join(Order).filter(
        Order.user_id == user_id,
        OrderItem.book_id == book_id,
        Order.status == 'completed'
    ).first()
    
    if not user_order:
        flash('You can only review books you have purchased.', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # Ensure user hasn't already reviewed
    existing_review = BookReview.query.filter_by(
        book_id=book_id, 
        user_id=user_id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this book.', 'info')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # Get form data
    rating = request.form.get('rating')
    review_text = request.form.get('review_text', '').strip()
    
    if not rating:
        flash('Please provide a rating.', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # Create new review
    review = BookReview(
        book_id=book_id,
        user_id=user_id,
        rating=int(rating),
        review_text=review_text if review_text else None
    )
    
    db.session.add(review)
    
    # Update book rating
    all_reviews = BookReview.query.filter_by(book_id=book_id).all()
    total_reviews = len(all_reviews) + 1  # include new one
    total_rating = sum(r.rating for r in all_reviews) + int(rating)
    book.avg_rating = total_rating / total_reviews
    book.review_count = total_reviews
    
    db.session.commit()
    
    flash('Your review has been added successfully!', 'success')
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/certifications')
def certifications():
    courses = Course.query.all()
    return render_template('certifications.html', courses=courses)

@app.route('/buy/<int:book_id>')
def buy_now(book_id):
    # Get the book details
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    # Use first image filename if exists, else None
    image_filename = book.images[0].image_filename if book.images else None

    # Use first category and subcategory names (or None if not set)
    category_name = book.categories[0].name if book.categories else None
    subcategory_name = book.subcategories[0].name if book.subcategories else None
    
    # Create a cart with just this item
    cart_item = {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': book.price,
        'image': image_filename,
        'category': category_name,
        'subject': subcategory_name,
        'quantity': 1
    }
    
    # Replace the entire cart with just this item for direct checkout
    session['cart'] = [cart_item]
    
    return redirect(url_for('checkout'))


@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total_price=total_price)


@app.route('/cart/add/<int:book_id>')
def add_to_cart(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    # Use first image filename if exists, else None
    image_filename = book.images[0].image_filename if book.images else None
    category_name = book.categories[0].name if book.categories else None
    subcategory_name = book.subcategories[0].name if book.subcategories else None

    cart_item = {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': book.price,
        'image': image_filename,
        'category': category_name,
        'subject': subcategory_name,
        'quantity': 1
    }

    cart = session.get('cart', [])

    for item in cart:
        if item['id'] == book.id:
            if item['quantity'] < book.quantity:
                item['quantity'] += 1
                flash(f"Increased quantity of '{book.title}' in cart.", "success")
            else:
                flash(f"Cannot add more '{book.title}'. Only {book.quantity} in stock.", "warning")
            break
    else:
        cart.append(cart_item)
        flash(f"'{book.title}' added to cart!", "success")

    session['cart'] = cart
    return redirect(url_for('cart'))


def create_bundle_cart_item(bundle):
    """Helper function to create standardized bundle cart item structure"""
    books_info = []
    for book in bundle.books:
        image_filename = book.images[0].image_filename if book.images else None
        books_info.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'price': book.price,
            'image': image_filename
        })
    
    return {
        'id': bundle.id,
        'title': bundle.title,
        'price': bundle.selling_price,
        'quantity': 1,
        'type': 'bundle',
        'books': books_info
    }


@app.route('/cart/add-bundle/<int:bundle_id>')
def add_bundle_to_cart(bundle_id):
    bundle = db.session.get(BundleOffer, bundle_id)
    if not bundle:
        abort(404)
    
    if not bundle.is_active:
        flash(f"Bundle '{bundle.title}' is no longer available.", "danger")
        return redirect(request.referrer or url_for('cart'))
    
    cart_item = create_bundle_cart_item(bundle)
    cart = session.get('cart', [])
    
    # Check if bundle already in cart
    for item in cart:
        if item.get('type') == 'bundle' and item['id'] == bundle_id:
            # Check stock availability for all books in bundle
            stock_available = True
            for book in bundle.books:
                if book.quantity < (item['quantity'] + 1):
                    stock_available = False
                    flash(f"Cannot add more '{bundle.title}'. Book '{book.title}' has insufficient stock.", "warning")
                    break
            
            if stock_available:
                item['quantity'] += 1
                flash(f"Increased quantity of bundle '{bundle.title}' in cart.", "success")
            break
    else:
        # Check stock for new bundle
        stock_available = True
        for book in bundle.books:
            if book.quantity < 1:
                stock_available = False
                flash(f"Cannot add bundle '{bundle.title}'. Book '{book.title}' is out of stock.", "warning")
                break
        
        if stock_available:
            cart.append(cart_item)
            flash(f"Bundle '{bundle.title}' added to cart!", "success")
    
    session['cart'] = cart
    return redirect(url_for('cart'))


@app.route('/cart/remove/<string:item_type>/<int:item_id>')
def remove_from_cart_generic(item_type, item_id):
    cart = session.get('cart', [])
    updated_cart = []
    
    for item in cart:
        if item_type == 'bundle':
            if not (item.get('type') == 'bundle' and item['id'] == item_id):
                updated_cart.append(item)
        elif item_type == 'course':
            if not (item.get('type') == 'course' and item['id'] == item_id):
                updated_cart.append(item)
        else:  # book
            if not (item.get('type', 'book') == 'book' and item['id'] == item_id):
                updated_cart.append(item)
    
    if len(cart) == len(updated_cart):
        flash("Item not found in cart.", "danger")
    else:
        session['cart'] = updated_cart
        item_name = "Bundle" if item_type == 'bundle' else ("Course" if item_type == 'course' else "Book")
        flash(f"{item_name} removed from cart.", "warning")
    
    return redirect(url_for('cart'))


# Keep old route for backward compatibility
@app.route('/cart/remove/<int:book_id>')
def remove_from_cart(book_id):
    return remove_from_cart_generic('book', book_id)


@app.route('/checkout')
@login_required
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty. Add items before checking out.", "info")
        return redirect(url_for('cart'))

    total_price = sum(item['price'] * item['quantity'] for item in cart)
    customer_form = CustomerForm()
    return render_template('checkout.html', cart=cart, total_price=total_price, customer_form=customer_form, razorpay_key=app.config['RAZORPAY_KEY_ID'])

@app.route('/payment/success')
@login_required
def payment_success():
    payment_id = request.args.get('payment_id', 'N/A')

    # Fetch cart and customer info from session
    cart = session.get('cart', [])
    customer_info = session.get('customer_info')
    
    # Validate that customer_info exists and has required fields
    if not customer_info:
        flash('Customer information is missing. Please complete your order again.', 'error')
        return redirect(url_for('checkout'))
    
    # Check for required customer information fields
    required_fields = ['full_name', 'email', 'phone']
    missing_fields = [field for field in required_fields if not customer_info.get(field, '').strip()]
    if missing_fields:
        flash(f'Missing required customer information: {", ".join(missing_fields)}. Please complete your order again.', 'error')
        return redirect(url_for('checkout'))

    full_name = customer_info.get('full_name', '')
    email = customer_info.get('email', '')
    phone = customer_info.get('phone', '')
    address = customer_info.get('address', '')

    # Calculate final price with optional shipping and tax
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    delivery_charge = 60 if total_price < 500 else 0
    final_amount = round(total_price + delivery_charge, 2)

    if 'user_id' in session:
        user_id = session['user_id']

        # 0. Create or update Customer record
        customer = get_or_create_customer(user_id, customer_info)
        customer_id = customer.id if customer else None

        # Stock validation pass - Check availability before processing payment
        for item in cart:
            item_type = item.get('type', 'book')
            item_id = item['id']
            quantity = item.get('quantity', 1)
            
            if item_type == 'bundle':
                bundle = db.session.get(BundleOffer, item_id)
                if not bundle or not bundle.is_active:
                    flash(f"Bundle '{item.get('title', 'Unknown')}' is no longer available.", "danger")
                    db.session.rollback()
                    return redirect(url_for('cart'))
                
                # Check stock for each book in bundle
                for book in bundle.books:
                    if book.quantity < quantity:
                        flash(f"Insufficient stock for '{book.title}' in bundle '{bundle.title}'. Only {book.quantity} available.", "danger")
                        db.session.rollback()
                        return redirect(url_for('cart'))
            elif item_type == 'book':
                book = db.session.get(Book, item_id)
                if not book or book.quantity < quantity:
                    available = book.quantity if book else 0
                    flash(f"Insufficient stock for '{item.get('title', 'Unknown')}'. Only {available} available.", "danger")
                    db.session.rollback()
                    return redirect(url_for('cart'))

        # 1. Create the Order
        order = Order(
            user_id=user_id,
            status='completed',
            date_created=datetime.now(timezone.utc),
            total_amount=final_amount
        )
        db.session.add(order)
        db.session.flush()  # Generates order.id

        # Generate custom order ID
        custom_order_id = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{payment_id[-6:]}"  # <-- Custom ID

        # 2. Add Order Items or Enroll in Courses
        for item in cart:
            item_type = item.get('type', 'book')
            item_id = item['id']
            title = item.get('title', 'Untitled')
            quantity = item.get('quantity', 1)
            price = item.get('price', 0.0)

            if item_type == 'course':
                user_course = UserCourse(
                    user_id=user_id,
                    course_id=item_id,
                    enrollment_date=datetime.now(timezone.utc),
                    completion_status='enrolled'
                )
                db.session.add(user_course)
                flash(f"Enrolled in course: {title}", 'success')
            elif item_type == 'bundle':
                # Handle bundle purchase
                bundle = db.session.get(BundleOffer, item_id)
                if bundle and bundle.is_active:
                    # Calculate per-book price allocation
                    per_book_price = bundle.selling_price / len(bundle.books) if bundle.books else 0
                    
                    # Create OrderItem for each book in the bundle
                    for book in bundle.books:
                        order_item = OrderItem(
                            order_id=order.id,
                            book_id=book.id,
                            quantity=quantity,
                            price=per_book_price
                        )
                        db.session.add(order_item)
                        
                        # Deduct quantity from Book table
                        if book.quantity >= quantity:
                            book.quantity -= quantity
                        else:
                            flash(f"Only {book.quantity} of '{book.title}' available in bundle. Adjusted to 0.", "warning")
                            book.quantity = 0
                        db.session.add(book)
                    
                    flash(f"Bundle purchased: {title}", 'success')
                else:
                    flash(f"Bundle '{title}' is no longer available.", "warning")
            else:
                # Add to order items (individual book)
                order_item = OrderItem(
                    order_id=order.id,
                    book_id=item_id,
                    quantity=quantity,
                    price=price
                )
                db.session.add(order_item)

                # Deduct quantity from Book table
                book = db.session.get(Book, item_id)
                if book:
                    if book.quantity >= quantity:
                        book.quantity -= quantity
                    else:
                        flash(f"Only {book.quantity} of '{book.title}' available. Adjusted to 0.", "warning")
                        book.quantity = 0
                    db.session.add(book)

        # 3. Create the Transaction
        transaction = Transaction(
            user_id=user_id,
            order_id=order.id,
            amount=final_amount,
            status='completed',
            payment_id=payment_id,
            date_created=datetime.now(timezone.utc)
        )
        db.session.add(transaction)
        db.session.flush()

        # 4. Create Full Order Details for each item
        for item in cart:
            item_type = item.get('type', 'book')
            
            full_detail = FullOrderDetail(
                order_id=order.id,
                transaction_id=transaction.id,
                customer_id=customer_id,
                bundle_id=item['id'] if item_type == 'bundle' else None,
                custom_order_id=custom_order_id,
                item_id=item['id'],
                item_type=item_type,
                item_title=item.get('title', 'Untitled'),
                quantity=item.get('quantity', 1),
                price=item['price'],
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(full_detail)

        db.session.commit()

    session['cart'] = []
    session.pop('customer_info', None)

    order_summary = {
        'order_id': custom_order_id,
        'payment_id': payment_id,
        'payment_date': datetime.now(timezone.utc).strftime('%B %d, %Y'),
        'amount': final_amount
    }

    return render_template('payment_success.html', **order_summary)


@app.route('/certificate/<int:certificate_id>')
def download_certificate(certificate_id):
    # Check if user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to download certificates.', 'warning')
        return redirect(url_for('login'))
    
    # Get the certificate
    certificate = db.session.get(Certificate, certificate_id)
    if not certificate:
        abort(404)
    
    # Check if the certificate belongs to the logged-in user
    if certificate.user_id != session['user_id']:
        flash('You do not have permission to access this certificate.', 'danger')
        return redirect(url_for('profile'))
    
    # Get the upload folder path
    upload_folder = app.config['UPLOAD_FOLDER']
    
    # Get original file extension
    file_extension = os.path.splitext(certificate.filename)[1]
    
    # Return the certificate file with correct extension
    return send_from_directory(
        os.path.join(upload_folder, 'certificates'),
        certificate.filename,
        as_attachment=True,
        download_name=f"certificate_{certificate.course_id}{file_extension}"
    )

@app.route('/enroll-course/<int:course_id>')
def enroll_course(course_id):
    # Check if user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to enroll in courses.', 'warning')
        return redirect(url_for('login'))
    
    # Get the course
    course = db.session.get(Course, course_id)
    if not course:
        abort(404)
    
    # Check if user is already enrolled
    existing_enrollment = UserCourse.query.filter_by(
        user_id=session['user_id'],
        course_id=course_id
    ).first()
    
    if existing_enrollment:
        flash(f'You are already enrolled in {course.title}.', 'info')
        return redirect(url_for('profile'))
    else:
        # Create cart item for the course
        cart_item = {
            'id': course.id,
            'title': course.title,
            'price': course.price,
            'image': course.image,
            'quantity': 1,
            'type': 'course'  # To distinguish from books
        }
        
        # Replace the entire cart with just this course for direct checkout
        session['cart'] = [cart_item]
        
        # Redirect to checkout for payment
        flash(f'Please complete the payment to enroll in {course.title}.', 'info')
        return redirect(url_for('checkout'))
    
# Career Page
@app.route('/careers', methods=['GET', 'POST'])
def careers():
    form = JobApplicationForm()
    jobs = Job.query.order_by(Job.posted_on.desc()).all()

    if form.validate_on_submit():
        resume_file = form.resume.data
        filename = secure_filename(resume_file.filename)
        filepath = os.path.join('static/resumes', filename)
        resume_file.save(filepath)

        application = JobApplication(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            resume=filepath,
            job_id=int(request.form['job_id'])  # Hidden input in form
        )
        db.session.add(application)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('careers'))

    return render_template('careers.html', jobs=jobs, form=form)


# Admin Job Posting Page
@app.route('/admin/jobs', methods=['GET', 'POST'])
@admin_login_required  #  only admins can access
def admin_jobs():
    form = JobForm()
    jobs = Job.query.order_by(Job.posted_on.desc()).all()

    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data
        )
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('admin_jobs'))

    return render_template('admin_jobs.html', form=form, jobs=jobs)


# Admin Application Viewer
@app.route('/admin/applications/<int:job_id>')
@admin_login_required  #  only admins can access
def view_applications(job_id):
    applications = JobApplication.query.filter_by(job_id=job_id).all()
    job = Job.query.get_or_404(job_id)
    return render_template('view_applications.html', job=job, applications=applications)

@app.route('/admin/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Optionally, delete associated applications
    for app in job.applications:
        db.session.delete(app)

    db.session.delete(job)
    db.session.commit()
    flash('Job and associated applications deleted successfully.', 'success')
    return redirect(url_for('admin_jobs'))  # change to your jobs listing route

@app.route('/admin/hero-slider', methods=['GET', 'POST'])
@admin_login_required  #  only admins can access
def admin_hero_slider():
    form = HeroSliderForm()

    if form.validate_on_submit():
        new_slide = HeroSlider(
            title=form.title.data,
            description=form.description.data,
            button_text=form.button_text.data,
            button_url=form.button_url.data
        )

        # Handle PC image upload
        if form.image.data:
            image_file = form.image.data
            filename = secure_filename(image_file.filename)
            folder_path = os.path.join(app.root_path, 'static/images')
            os.makedirs(folder_path, exist_ok=True)
            img_path = os.path.join(folder_path, filename)
            image_file.save(img_path)
            new_slide.image = f'images/{filename}'

        # Handle mobile image upload
        if form.mobile_image.data:
            mobile_image_file = form.mobile_image.data
            mobile_filename = secure_filename(mobile_image_file.filename)
            # Add mobile suffix to filename
            name, ext = os.path.splitext(mobile_filename)
            mobile_filename = f"{name}_mobile{ext}"
            folder_path = os.path.join(app.root_path, 'static/images')
            os.makedirs(folder_path, exist_ok=True)
            mobile_img_path = os.path.join(folder_path, mobile_filename)
            mobile_image_file.save(mobile_img_path)
            new_slide.mobile_image = f'images/{mobile_filename}'

        db.session.add(new_slide)
        db.session.commit()
        flash('New slide added!', 'success')
        return redirect(url_for('admin_hero_slider'))

    slides = HeroSlider.query.order_by(HeroSlider.updated_at.desc()).all()
    return render_template('admin_hero_slider.html', form=form, slides=slides)

@app.route('/admin/hero-slider/delete/<int:slide_id>', methods=['POST'])
@admin_login_required
def delete_hero_slide(slide_id):
    slide = db.session.get(HeroSlider, slide_id)
    if slide:
        # Delete the PC image file if it exists
        if slide.image:
            image_path = os.path.join(app.root_path, 'static', slide.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # Delete the mobile image file if it exists
        if slide.mobile_image:
            mobile_image_path = os.path.join(app.root_path, 'static', slide.mobile_image)
            if os.path.exists(mobile_image_path):
                os.remove(mobile_image_path)
        
        db.session.delete(slide)
        db.session.commit()
        flash('Slide deleted successfully!', 'success')
    else:
        flash('Slide not found!', 'danger')
    
    return redirect(url_for('admin_hero_slider'))

@app.route('/admin/testimonials', methods=['GET', 'POST'])
@admin_login_required  #  only admins can access
def manage_testimonials():
    form = TestimonialForm()
    if form.validate_on_submit():
        image_file = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(image_path)
            image_file = filename

        testimonial = Testimonial(
            name=form.name.data,
            role=form.role.data,
            message=form.message.data,
            image=image_file
        )
        db.session.add(testimonial)
        db.session.commit()
        flash('Testimonial added successfully!', 'success')
        return redirect(url_for('manage_testimonials'))

    testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('admin/manage_testimonials.html', form=form, testimonials=testimonials)

@app.route('/add-book', methods=['GET', 'POST'])
@admin_login_required
def add_book():
    form = BookForm()
    
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            description=form.description.data,
            quantity=int(form.quantity.data),
            original_price=form.original_price.data,
            price=float(form.price.data)
        )

        # Add multiple categories & subcategories
        book.categories.extend(form.categories.data)
        book.subcategories.extend(form.subcategories.data)

        db.session.add(book)
        db.session.flush()  # get book.id

        # Handle image uploads
        if form.images.data:
            upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'books')
            os.makedirs(upload_folder, exist_ok=True)
            
            for file in form.images.data:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)

                    image = BookImage(image_filename=filename, book_id=book.id)
                    db.session.add(image)

        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin.manage_books'))

    return render_template('add_book.html', form=form)

@app.route('/manage-categories', methods=['GET', 'POST'])
@admin_login_required  #  only admins can access
def manage_categories():
    category_form = CategoryForm()
    subcategory_form = SubCategoryForm()
    subcategory_form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    categories = Category.query.all()

    return render_template("manage_category.html",
                           category_form=category_form,
                           subcategory_form=subcategory_form,
                           categories=categories)

@app.route('/add-category', methods=['POST'])
@admin_login_required  #  only admins can access
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        db.session.add(Category(name=form.name.data))
        db.session.commit()
    return redirect(url_for('manage_categories'))

@app.route('/add-subcategory', methods=['POST'])
@admin_login_required  #  only admins can access
def add_subcategory():
    form = SubCategoryForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        db.session.add(SubCategory(name=form.name.data, category_id=form.category_id.data))
        db.session.commit()
    return redirect(url_for('manage_categories'))



@app.route('/update-category/<int:category_id>', methods=['POST'])
@admin_login_required
def update_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        flash('Category not found', 'danger')
        return redirect(url_for('manage_categories'))
    
    name = request.form.get('name')
    if name:
        category.name = name
        db.session.commit()
        flash('Category updated successfully', 'success')
    
    return redirect(url_for('manage_categories'))

@app.route('/delete-category/<int:category_id>')
@admin_login_required
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        flash('Category not found', 'danger')
        return redirect(url_for('manage_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully', 'success')
    
    return redirect(url_for('manage_categories'))

@app.route('/update-subcategory/<int:subcategory_id>', methods=['POST'])
@admin_login_required
def update_subcategory(subcategory_id):
    subcategory = db.session.get(SubCategory, subcategory_id)
    if not subcategory:
        flash('Subcategory not found', 'danger')
        return redirect(url_for('manage_categories'))
    
    name = request.form.get('name')
    category_id = request.form.get('category_id')
    
    if name:
        subcategory.name = name
    
    if category_id and category_id.isdigit():
        subcategory.category_id = int(category_id)
    
    db.session.commit()
    flash('Subcategory updated successfully', 'success')
    
    return redirect(url_for('manage_categories'))

@app.route('/delete-subcategory/<int:subcategory_id>')
@admin_login_required
def delete_subcategory(subcategory_id):
    subcategory = db.session.get(SubCategory, subcategory_id)
    if not subcategory:
        flash('Subcategory not found', 'danger')
        return redirect(url_for('manage_categories'))
    
    db.session.delete(subcategory)
    db.session.commit()
    flash('Subcategory deleted successfully', 'success')
    
    return redirect(url_for('manage_categories'))

@app.route('/store-customer-info', methods=['POST'])
def store_customer_info():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['full_name', 'email', 'phone', 'street_address', 'city', 'state', 'pincode']
    for field in required_fields:
        if not data.get(field, '').strip():
            return jsonify({'status': 'error', 'message': f'{field.replace("_", " ").title()} is required'}), 400
    
    # Server-side regex validation for pincode (exactly 6 digits)
    pincode = data.get('pincode', '').strip()
    if not re.match(r'^\d{6}$', pincode):
        return jsonify({'status': 'error', 'message': 'Pincode must be exactly 6 digits'}), 400
    
    # Server-side regex validation for phone (10-15 digits)
    phone = data.get('phone', '').strip()
    if not re.match(r'^\d{10,15}$', phone):
        return jsonify({'status': 'error', 'message': 'Phone number must be 10-15 digits'}), 400
    
    # Store detailed customer information in session
    session['customer_info'] = {
        'full_name': data.get('full_name', '').strip(),
        'email': data.get('email', '').strip(),
        'phone': phone,
        'street_address': data.get('street_address', '').strip(),
        'city': data.get('city', '').strip(),
        'state': data.get('state', '').strip(),
        'pincode': pincode,
        # Keep backward compatibility with single address field
        'address': f"{data.get('street_address', '')}, {data.get('city', '')}, {data.get('state', '')} - {pincode}"
    }
    return jsonify({'status': 'success', 'message': 'Customer information saved successfully'}), 200

@app.route('/admin/full-orders')
@admin_login_required  # Only admins can access
def admin_view_full_orders():
    full_orders = FullOrderDetail.query\
        .join(Order, FullOrderDetail.order_id == Order.id)\
        .outerjoin(Transaction, FullOrderDetail.transaction_id == Transaction.id)\
        .outerjoin(Customer, FullOrderDetail.customer_id == Customer.id)\
        .options(
            db.contains_eager(FullOrderDetail.order),
            db.contains_eager(FullOrderDetail.transaction),
            db.contains_eager(FullOrderDetail.customer)
        )\
        .order_by(FullOrderDetail.created_at.desc())\
        .all()

    return render_template('admin/full_orders.html', full_orders=full_orders)



@app.route('/admin/full-orders/delete/<int:order_id>', methods=['POST'])
@admin_login_required  # Only admins can access
def admin_delete_full_order(order_id):
    full_order = FullOrderDetail.query.filter_by(id=order_id).first()
    if full_order:
        db.session.delete(full_order)
        db.session.commit()
        flash('Order record deleted successfully.', 'success')
    else:
        flash('Order not found.', 'danger')

    return redirect(url_for('admin_view_full_orders'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'results': {}})

    results = {
        'courses': [],          # TODO: Fill in when course model is ready
        'books': [],
        'certifications': []    # TODO: Fill in when certification model is ready
    }

    # --- Books search ---
    books_query = (
        Book.query
        .filter(Book.is_deleted == False)
        .filter(
            db.or_(
                Book.title.ilike(f"%{query}%"),
                Book.author.ilike(f"%{query}%"),
                Book.description.ilike(f"%{query}%"),
                Book.categories.any(Category.name.ilike(f"%{query}%")),
                Book.subcategories.any(SubCategory.name.ilike(f"%{query}%"))
            )
        )
        .limit(20)
        .all()
    )

    for book in books_query:
        results['books'].append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'description': book.description or '',
            'price': book.price,
            'categories': [c.name for c in book.categories],
            'subcategories': [s.name for s in book.subcategories],
            'avg_rating': book.avg_rating,
            'review_count': book.review_count
        })

    return jsonify({'success': True, 'results': results})


@app.route('/search/suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip().lower()
    category = request.args.get('category', 'all')

    if not query or len(query) < 2:
        return jsonify({'success': False, 'suggestions': []})

    suggestions = []

    # Direct matches for courses and certifications
    if 'course'.startswith(query):
        suggestions.append({
            'text': 'Courses',
            'category': 'courses',
            'id': 0
        })

    if 'certification'.startswith(query):
        suggestions.append({
            'text': 'Certifications',
            'category': 'certifications',
            'id': 0
        })

    # --- Book suggestions ---
    if category in ('all', 'books'):
        books = (
            Book.query
            .filter(Book.is_deleted == False)
            .filter(Book.title.ilike(f"%{query}%"))
            .limit(5)
            .all()
        )
        for book in books:
            suggestions.append({
                'text': book.title,
                'category': 'books',
                'id': book.id
            })

    # --- Category suggestions ---
    if category in ('all', 'books'):
        cats = Category.query.filter(Category.name.ilike(f"%{query}%")).limit(5).all()
        for cat in cats:
            suggestions.append({
                'text': cat.name,
                'category': 'category',
                'id': cat.id
            })

    # --- SubCategory suggestions ---
    if category in ('all', 'books'):
        subs = SubCategory.query.filter(SubCategory.name.ilike(f"%{query}%")).limit(5).all()
        for sub in subs:
            suggestions.append({
                'text': sub.name,
                'category': 'subcategory',
                'id': sub.id
            })

    return jsonify({'success': True, 'suggestions': suggestions})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)

