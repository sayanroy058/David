from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from models import  db, Course, Teacher, BookImage, Admin, Certificate, User, UserCourse
from forms import CourseForm, TeacherForm, AdminLoginForm, AdminRegistrationForm, CertificateUploadForm
from models import db, Book, Order, OrderItem, Transaction
from forms import BookForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

UPLOAD_FOLDER = 'static/uploads/'

# Admin login required decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(email=form.email.data).first()
        if admin and check_password_hash(admin.password_hash, form.password.data):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            session['admin_email'] = admin.email
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('admin/login.html', form=form)

@admin_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        # Check if admin code is correct
        if form.admin_code.data != 'Dav@4321':  # Simple admin code for demonstration
            flash('Invalid admin code.', 'danger')
            return render_template('admin/register.html', form=form)
            
        # Check if email already exists
        existing_admin = Admin.query.filter_by(email=form.email.data).first()
        if existing_admin:
            flash('Email already registered.', 'danger')
            return render_template('admin/register.html', form=form)
            
        hashed_password = generate_password_hash(form.password.data)
        admin = Admin(
            name=form.name.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(admin)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('admin.login'))
    return render_template('admin/register.html', form=form)

@admin_bp.route('/logout')
@admin_login_required
def logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@admin_login_required
def dashboard():
    admin = db.session.get(Admin, session['admin_id'])
    
    # Get statistics for dashboard
    user_count = User.query.count()
    course_count = Course.query.count()
    book_count = Book.query.count()
    certificate_count = Certificate.query.count()
    
    # Create stats dictionary for template
    stats = {
        'users': user_count,
        'courses': course_count,
        'books': book_count,
        'certificates': certificate_count,
        'orders': Order.query.count()
    }
    
    # Get recent certificates
    recent_certificates = Certificate.query.order_by(Certificate.upload_date.desc()).limit(5).all()
    
    # Get recent orders from database
    recent_orders = []
    try:
        orders = Order.query.order_by(Order.date_created.desc()).limit(5).all()
        for order in orders:
            # Calculate total amount for the order
            total_amount = sum(item.price * item.quantity for item in order.items)
            
            # Get user email
            user_email = order.user.email if order.user else 'Unknown'
            
            # Determine status class
            status_class = {
                'completed': 'success',
                'processing': 'warning',
                'pending': 'warning',
                'cancelled': 'danger'
            }.get(order.status.lower(), 'secondary')
            
            recent_orders.append({
                'id': order.id,
                'user_email': user_email,
                'amount': total_amount,
                'date': order.date_created.strftime('%Y-%m-%d'),
                'status': order.status.capitalize(),
                'status_class': status_class
            })
    except Exception as e:
        # Handle case where Order table might not exist or other database errors
        print(f"Error fetching orders: {e}")
    
    # Get all users for user management section
    all_users = User.query.all()
    
    # Create certificate form with user email dropdown
    certificate_form = CertificateUploadForm()
    
    # Populate the user email dropdown
    user_choices = [(user.email, user.email) for user in all_users]
    certificate_form.user_email.choices = user_choices
    
    return render_template('admin/dashboard.html', 
                           admin=admin,
                           stats=stats,
                           user_count=user_count,
                           course_count=course_count,
                           book_count=book_count,
                           certificate_count=certificate_count,
                           recent_certificates=recent_certificates,
                           recent_orders=recent_orders,
                           certificate_form=certificate_form,
                           users=all_users)

@admin_bp.route('/add-course', methods=['GET', 'POST'])
@admin_login_required
def add_course():
    form = CourseForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(image_path)

        course = Course(
            title=form.title.data,
            description=form.description.data,
            image_filename=filename
        )
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('admin.add_course'))
    return render_template('admin/add_course.html', form=form)


@admin_bp.route('/manage-books')
@admin_login_required
def manage_books():
    books = Book.query.all()
    return render_template('admin/manage_books.html', books=books)

@admin_bp.route('/upload-certificate', methods=['GET', 'POST'])
@admin_login_required
def upload_certificate():
    form = CertificateUploadForm()
    if form.validate_on_submit():
        # Validate user exists
        user = User.query.filter_by(email=form.user_email.data).first()
        if not user:
            flash('User with this email does not exist.', 'danger')
            return render_template('admin/upload_certificate.html', form=form)
        
        # Validate course exists
        course = db.session.get(Course, form.course_id.data)
        if not course:
            flash('Course with this ID does not exist.', 'danger')
            return render_template('admin/upload_certificate.html', form=form)
        
        # Save certificate file
        filename = secure_filename(form.certificate.data.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        form.certificate.data.save(filepath)
        
        # Create certificate record
        certificate = Certificate(
            user_id=user.id,
            course_id=course.id,
            filename=filename
        )
        db.session.add(certificate)
        db.session.commit()
        
        flash('Certificate uploaded successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    # Get all users for dropdown
    users = User.query.all()
    
    return render_template('admin/upload_certificate.html', form=form, users=users)

@admin_bp.route('/certificate/<int:certificate_id>')
@admin_login_required
def view_certificate(certificate_id):
    certificate = db.session.get(Certificate, certificate_id)
    if not certificate:
        abort(404)
    return render_template('admin/view_certificate.html', certificate=certificate)

@admin_bp.route('/certificate/delete/<int:certificate_id>')
@admin_login_required
def delete_certificate(certificate_id):
    certificate = db.session.get(Certificate, certificate_id)
    if not certificate:
        abort(404)
    
    # Delete file from filesystem
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', certificate.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    db.session.delete(certificate)
    db.session.commit()
    
    flash('Certificate deleted successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/user/view/<int:user_id>')
@admin_login_required
def view_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    
    # Get user courses
    user_courses = UserCourse.query.filter_by(user_id=user.id).all()
    
    # Get user certificates
    user_certificates = Certificate.query.filter_by(user_id=user.id).all()
    
    # Get user orders
    user_orders = Order.query.filter_by(user_id=user.id).all()
    
    return render_template('admin/view_user.html', 
                           user=user,
                           user_courses=user_courses,
                           user_certificates=user_certificates,
                           user_orders=user_orders)

@admin_bp.route('/edit-book/<int:book_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    form = BookForm(obj=book)

    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.description = form.description.data
        book.category = form.category.data
        book.subject = form.subject.data
        book.quantity = int(form.quantity.data)
        book.price = float(form.price.data)
        book.original_price=form.original_price.data  # Now it returns float or None directly



        # Handle image deletions
        delete_image_ids = request.form.getlist('delete_images')
        for img_id in delete_image_ids:
            image_to_delete = db.session.get(BookImage, img_id)
            if image_to_delete:
                # Delete file from filesystem
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], image_to_delete.image_filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                db.session.delete(image_to_delete)

        # Handle new image uploads
        if form.images.data:
            for img in form.images.data:
                if img.filename:
                    filename = secure_filename(img.filename)
                    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    img.save(image_path)
                    book_image = BookImage(
                        image_filename=filename,
                        book_id=book.id
                    )
                    db.session.add(book_image)

        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin.manage_books'))

    return render_template('admin/edit_book.html', form=form, book=book)

@admin_bp.route('/delete-book/<int:book_id>', methods=['POST'])
@admin_login_required
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    for image in book.images:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(image)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin.manage_books'))

@admin_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    
    if request.method == 'POST':
        # Update user information
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        
        db.session.commit()
        flash('User information updated successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/edit_user.html', user=user)

