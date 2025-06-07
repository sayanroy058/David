from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_from_directory, abort, current_app
from models import Book, BookImage, Category, HeroSlider, Job, JobApplication, SubCategory, Testimonial, db, Course, Teacher, User, Order, OrderItem, Transaction, Certificate, UserCourse
from modelss.data import get_courses, get_books, get_certifications 
from admin_routes import admin_bp, admin_login_required
from forms import BookForm, CategoryForm, HeroSliderForm, JobApplicationForm, JobForm, RegistrationForm, LoginForm, SubCategoryForm, TestimonialForm
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import razorpay
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Razorpay configuration
app.config['RAZORPAY_KEY_ID'] = 'rzp_test_vntVc372QhJLXH'
app.config['RAZORPAY_KEY_SECRET'] = 'fsWX6EnEFSUQBs0ftrwcIVLg'
razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))

# Initialize DB
db.init_app(app)

# Register Blueprints
app.register_blueprint(admin_bp)

# Routes
@app.route('/')
def index():
    courses = Course.query.filter_by(is_popular=True).all()
    teachers = Teacher.query.all()
    hero_slides = HeroSlider.query.order_by(HeroSlider.updated_at.desc()).all()
    testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('index.html', courses=courses, teachers=teachers, hero_slides=hero_slides, testimonials=testimonials)

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
    query = Book.query

    title = request.args.get('title')
    author = request.args.get('author')
    category = request.args.get('category')  # Note: now using name, not ID
    subject = request.args.get('subject')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if category:
        query = query.filter(Book.category.ilike(f"%{category}%"))
    if subject:
        query = query.filter(Book.subject.ilike(f"%{subject}%"))
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    if max_price is not None:
        query = query.filter(Book.price <= max_price)

    books = query.all()
    
    # Fetch distinct category and subject names for filters
    categories = [c[0] for c in db.session.query(Book.category).distinct().all()]
    subjects = [s[0] for s in db.session.query(Book.subject).distinct().all()]

    return render_template(
        'books_new.html',
        books=books,
        categories=categories,
        subjects=subjects
    )

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
    
    # Create a cart with just this item
    cart_item = {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': book.price,
        'image': image_filename,
        'category': book.category,
        'subject': book.subject,
        'quantity': 1
    }
    
    # Replace the entire cart with just this item for direct checkout
    session['cart'] = [cart_item]
    
    # Redirect to checkout
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

    cart_item = {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': book.price,
        'image': image_filename,
        'category': book.category,
        'subject': book.subject,
        'quantity': 1
    }

    cart = session.get('cart', [])

    for item in cart:
        if item['id'] == book.id:
            # Optional: check stock before incrementing
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


@app.route('/cart/remove/<int:book_id>')
def remove_from_cart(book_id):
    cart = session.get('cart', [])

    updated_cart = [item for item in cart if item['id'] != book_id]

    if len(cart) == len(updated_cart):
        flash("Item not found in cart.", "danger")
    else:
        session['cart'] = updated_cart
        flash("Item removed from cart.", "warning")

    return redirect(url_for('cart'))


@app.route('/checkout')
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty. Add items before checking out.", "info")
        return redirect(url_for('cart'))

    total_price = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('checkout.html', cart=cart, total_price=total_price)

@app.route('/payment/success')
def payment_success():
    # Get payment details from Razorpay callback
    payment_id = request.args.get('payment_id', 'N/A')
    
    # In a real application, you would verify the payment with Razorpay here
    # and update your database with order information
    
    # Clear the cart after successful payment
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    
    # Calculate the final amount including tax
    final_amount = total_price * 1.05  # Including tax
    
    # Create order records in the database
    if 'user_id' in session:
        # Create a new order
        order = Order(
            user_id=session['user_id'],
            date_created=datetime.now(),
            status='completed',
            total_amount=final_amount  # Set the total amount including tax
        )
        db.session.add(order)
        db.session.flush()  # Get the order ID
        
        # Add order items
        for item in cart:
            # Check if this is a course or a book
            if item.get('type') == 'course':
                # Create course enrollment
                enrollment = UserCourse(
                    user_id=session['user_id'],
                    course_id=item['id'],
                    enrollment_date=datetime.now(),
                    completion_status='enrolled'
                )
                db.session.add(enrollment)
                flash(f"Successfully enrolled in {item['title']}!", 'success')
            else:
                # Regular book order item
                order_item = OrderItem(
                    order_id=order.id,
                    book_id=item['id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                db.session.add(order_item)
        
        # Create transaction record
        transaction = Transaction(
            user_id=session['user_id'],
            order_id=order.id,
            amount=final_amount,  # Use the same final amount
            payment_id=payment_id,
            status='completed',
            date_created=datetime.now()
        )
        db.session.add(transaction)
        db.session.commit()
    
    # Clear the cart
    session['cart'] = []
    
    # Generate order details for the template
    order_details = {
        'order_id': f"ORD-{datetime.now().strftime('%Y%m%d')}-{payment_id[-6:]}",
        'payment_id': payment_id,
        'payment_date': datetime.now().strftime('%B %d, %Y'),
        'amount': final_amount  # Use the same final amount
    }
    
    return render_template('payment_success.html', **order_details)

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
    
    # Return the certificate file
    return send_from_directory(
        os.path.join(upload_folder, 'certificates'),
        certificate.filename,
        as_attachment=True,
        download_name=f"certificate_{certificate.course_id}.pdf"
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
            button_text=form.button_text.data
        )

        if form.image.data:
            image_file = form.image.data
            filename = secure_filename(image_file.filename)
            folder_path = os.path.join(app.root_path, 'static/images')
            os.makedirs(folder_path, exist_ok=True)
            img_path = os.path.join(folder_path, filename)
            image_file.save(img_path)
            new_slide.image = f'images/{filename}'

        db.session.add(new_slide)
        db.session.commit()
        flash('New slide added!', 'success')
        return redirect(url_for('admin_hero_slider'))

    slides = HeroSlider.query.order_by(HeroSlider.updated_at.desc()).all()
    return render_template('admin_hero_slider.html', form=form, slides=slides)

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
@admin_login_required  #  only admins can access
def add_book():
    form = BookForm()
    
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            description=form.description.data,
            category=form.category.data,
            subject=form.subject.data,
            quantity=int(form.quantity.data),
            original_price=form.original_price.data,
            price=float(form.price.data)
        )
        db.session.add(book)
        db.session.flush()  #  Get book.id before committing

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
        return redirect(url_for('admin.manage_books'))  #  Redirect to book list/admin panel

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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

