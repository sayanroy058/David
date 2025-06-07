from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, send_from_directory, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Course, Teacher, Book, BookImage, Admin, User, Certificate, UserCourse, Order, OrderItem, Transaction
from forms import CourseForm, TeacherForm, BookForm, AdminRegistrationForm, AdminLoginForm, CertificateUploadForm
import os
from datetime import datetime
import uuid

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper function to check if admin is logged in
def admin_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in as admin to access this page.', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Login
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(email=form.email.data).first()
        if admin and check_password_hash(admin.password_hash, form.password.data):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('admin/login.html', form=form)

# Admin Registration
@admin_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        # Check if admin security code is correct
        if form.admin_code.data != 'Dav@4321':  # Simple example, use environment variable in production
            flash('Invalid admin security code', 'danger')
            return render_template('admin/register.html', form=form)
            
        # Check if email already exists
        existing_admin = Admin.query.filter_by(email=form.email.data).first()
        if existing_admin:
            flash('Email already registered', 'danger')
            return render_template('admin/register.html', form=form)
            
        # Create new admin
        hashed_password = generate_password_hash(form.password.data)
        new_admin = Admin(name=form.name.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(new_admin)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('admin.login'))
        
    return render_template('admin/register.html', form=form)

# Admin Logout
@admin_bp.route('/logout')
@admin_login_required
def logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('admin.login'))

# Admin Dashboard
@admin_bp.route('/dashboard')
@admin_login_required
def dashboard():
    # Get admin info
    admin = db.session.get(Admin, session['admin_id'])
    
    # Get statistics
    stats = {
        'users': User.query.count(),
        'courses': Course.query.count(),
        'books': Book.query.count(),
        'orders': Order.query.count()
    }
    
    # Get recent orders from database
    recent_orders_data = Order.query.order_by(Order.date_created.desc()).limit(5).all()
    recent_orders = []
    
    for order in recent_orders_data:
        # Use the stored total_amount if available, otherwise calculate it from items
        total_amount = order.total_amount if order.total_amount is not None else sum(item.price * item.quantity for item in order.items)
        
        # Get user email
        user_email = db.session.get(User, order.user_id).email if db.session.get(User, order.user_id) else 'Unknown'
        
        # Determine status class
        status_class = 'success' if order.status == 'completed' else 'warning' if order.status == 'processing' else 'danger'
        
        recent_orders.append({
            'id': order.id,
            'user_email': user_email,
            'amount': total_amount,
            'date': order.date_created.strftime('%Y-%m-%d'),
            'status': order.status.capitalize(),
            'status_class': status_class
        })
    
    # Get all users
    all_users = User.query.all()
    
    # Get certificates
    recent_certificates = Certificate.query.order_by(Certificate.upload_date.desc()).limit(10).all()
    
    # Recent activity (placeholder data)
    recent_activity = [
        {'text': 'New user registered', 'time': '10 minutes ago', 'icon': 'bi-person-plus', 'color': 'rgba(102, 126, 234, 0.8)'},
        {'text': 'New order placed', 'time': '1 hour ago', 'icon': 'bi-cart-plus', 'color': 'rgba(46, 204, 113, 0.8)'},
        {'text': 'Certificate uploaded', 'time': '3 hours ago', 'icon': 'bi-file-earmark-check', 'color': 'rgba(52, 152, 219, 0.8)'},
        {'text': 'New course added', 'time': '1 day ago', 'icon': 'bi-journal-plus', 'color': 'rgba(155, 89, 182, 0.8)'},
    ]
    
    # Certificate upload form with user dropdown
    certificate_form = CertificateUploadForm()
    certificate_form.user_email.choices = [(user.email, user.email) for user in all_users]
    
    return render_template('admin/dashboard.html', 
                           admin=admin, 
                           stats=stats, 
                           recent_orders=recent_orders,
                           users=all_users,
                           recent_certificates=recent_certificates,
                           recent_activity=recent_activity,
                           certificate_form=certificate_form)

# Add Course (existing route)
@admin_bp.route('/add-course', methods=['GET', 'POST'])
@admin_login_required
def add_course():
    form = CourseForm()
    
    # Populate teacher choices
    teachers = Teacher.query.all()
    form.teacher_id.choices = [(teacher.id, teacher.name) for teacher in teachers]
    
    if form.validate_on_submit():
        # Save the course image
        if form.image.data:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'courses', image_filename))
        else:
            image_filename = 'default-course.jpg'
            
        # Create new course
        new_course = Course(
            title=form.title.data,
            description=form.description.data,
            price=float(form.price.data),
            image=image_filename,
            teacher_id=form.teacher_id.data,
            is_certification=form.is_certification.data,
            subject=form.subject.data if form.is_certification.data else None,
            difficulty_level=form.difficulty_level.data if form.is_certification.data else None,
            duration=form.duration.data if form.is_certification.data else None
        )
        db.session.add(new_course)
        db.session.commit()
        
        flash('Course added successfully!', 'success')
        if form.is_certification.data:
            return redirect(url_for('admin.manage_certifications'))
        else:
            return redirect(url_for('admin.add_course'))
        
    return render_template('admin/add_course.html', form=form, teachers=teachers)

# Add Teacher (existing route)
@admin_bp.route('/add-teacher', methods=['GET', 'POST'])
@admin_login_required
def add_teacher():
    form = TeacherForm()
    if form.validate_on_submit():
        # Save the teacher image
        if form.image.data:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'teachers', image_filename))
        else:
            image_filename = 'default-teacher.jpg'
            
        # Create new teacher
        new_teacher = Teacher(
            name=form.name.data,
            title=form.title.data,
            photo=image_filename
        )
        db.session.add(new_teacher)
        db.session.commit()
        
        flash('Teacher added successfully!', 'success')
        return redirect(url_for('admin.manage_teachers'))
        
    return render_template('admin/add_teacher.html', form=form)

# Manage Teachers
@admin_bp.route('/manage-teachers')
@admin_login_required
def manage_teachers():
    # Get search and sort parameters
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'name_asc')
    
    # Start with base query
    query = Teacher.query
    
    # Apply search filter if provided
    if search:
        query = query.filter(Teacher.name.ilike(f'%{search}%'))
    
    # Apply sorting
    if sort_by == 'name_asc':
        query = query.order_by(Teacher.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Teacher.name.desc())
    
    # Get all teachers
    teachers = query.all()
    
    return render_template('admin/manage_teachers.html', teachers=teachers)

# Edit Teacher
@admin_bp.route('/edit-teacher/<int:teacher_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_teacher(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        abort(404)
    form = TeacherForm()
    
    if form.validate_on_submit():
        teacher.name = form.name.data
        teacher.title = form.title.data
        
        # Update image if a new one is provided
        if form.image.data:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'teachers', image_filename))
            teacher.photo = image_filename
        
        db.session.commit()
        flash('Teacher updated successfully!', 'success')
        return redirect(url_for('admin.manage_teachers'))
    
    # Pre-populate form fields
    form.name.data = teacher.name
    form.title.data = teacher.title
    
    return render_template('admin/edit_teacher.html', form=form, teacher=teacher)

# Delete Teacher
@admin_bp.route('/delete-teacher/<int:teacher_id>', methods=['POST'])
@admin_login_required
def delete_teacher(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        abort(404)
    
    # Check if teacher is associated with any courses
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    if courses:
        flash('Cannot delete teacher. Teacher is associated with one or more courses.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    db.session.delete(teacher)
    db.session.commit()
    
    flash('Teacher deleted successfully!', 'success')
    return redirect(url_for('admin.manage_teachers'))



# Manage Books
@admin_bp.route('/manage-books')
@admin_login_required
def manage_books():
    # Get search and filter parameters
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    sort_by = request.args.get('sort', 'title_asc')
    
    # Start with base query
    query = Book.query
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            db.or_(
                Book.title.ilike(f'%{search}%'),
                Book.author.ilike(f'%{search}%'),
                Book.description.ilike(f'%{search}%')
            )
        )
    
    # Apply category filter if provided
    if category_filter:
        query = query.filter(Book.category == category_filter)
    
    # Apply sorting
    if sort_by == 'title_asc':
        query = query.order_by(Book.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Book.title.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Book.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Book.price.desc())
    
    # Execute query
    books = query.all()
    
    # Get unique categories for filter dropdown
    categories = db.session.query(Book.category).distinct().filter(Book.category != None).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('admin/manage_books.html', books=books, categories=categories)

# Edit Book
@admin_bp.route('/edit-book/<int:book_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        # Update book details
        book.title = form.title.data
        book.author = form.author.data
        book.description = form.description.data
        book.price = float(form.price.data)
        book.category = form.category.data
        book.subject = form.subject.data
        book.quantity = int(form.quantity.data)
        
        # Handle image deletions if any
        delete_images = request.form.getlist('delete_images')
        if delete_images:
            for image_id in delete_images:
                image = db.session.get(BookImage, image_id)
                if image and image.book_id == book.id:
                    # Delete the file from filesystem
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', image.image_filename))
                    except Exception as e:
                        flash(f'Error deleting image file: {str(e)}', 'warning')
                    
                    # Delete from database
                    db.session.delete(image)
        
        # Handle new image uploads
        if form.images.data:
            for image in form.images.data:
                if image.filename:  # Check if a file was actually uploaded
                    image_filename = secure_filename(image.filename)
                    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', image_filename))
                    
                    # Create book image record
                    book_image = BookImage(image_filename=image_filename, book_id=book.id)
                    db.session.add(book_image)
        
        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin.manage_books'))
    
    return render_template('admin/edit_book.html', form=form, book=book)

# Delete Book
@admin_bp.route('/delete-book/<int:book_id>')
@admin_login_required
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    # Delete associated images from filesystem
    for image in book.images:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', image.image_filename))
        except Exception as e:
            flash(f'Error deleting image file: {str(e)}', 'warning')
    
    # Delete book and associated images from database
    # The cascade="all, delete-orphan" in the Book model will handle deleting associated images
    db.session.delete(book)
    db.session.commit()
    
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin.manage_books'))

# Upload Certificate
@admin_bp.route('/upload-certificate', methods=['GET', 'POST'])
@admin_login_required
def upload_certificate():
    # Get all users for the dropdown
    all_users = User.query.all()
    
    form = CertificateUploadForm()
    form.user_email.choices = [(user.email, user.email) for user in all_users]
    
    if request.method == 'GET':
        return render_template('admin/upload_certificate.html', form=form)
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.user_email.data).first()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin.dashboard'))
            
        # Check if course exists
        course = db.session.get(Course, form.course_id.data)
        if not course:
            flash('Course not found', 'danger')
            return redirect(url_for('admin.dashboard'))
            
        # Check if user is enrolled in the course
        user_course = UserCourse.query.filter_by(user_id=user.id, course_id=course.id).first()
        if not user_course:
            # Create user course enrollment if it doesn't exist
            user_course = UserCourse(user_id=user.id, course_id=course.id, completed=True)
            db.session.add(user_course)
            db.session.commit()
        
        # Save certificate file
        if form.certificate.data:
            # Generate unique filename
            filename = f"{uuid.uuid4().hex}_{secure_filename(form.certificate.data.filename)}"
            certificate_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(certificate_path), exist_ok=True)
            
            # Save file
            form.certificate.data.save(certificate_path)
            
            # Create certificate record
            certificate = Certificate(
                user_id=user.id,
                course_id=course.id,
                filename=filename,
                upload_date=datetime.now()
            )
            db.session.add(certificate)
            db.session.commit()
            
            flash('Certificate uploaded successfully', 'success')
        else:
            flash('No certificate file provided', 'danger')
            
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
                
    return redirect(url_for('admin.dashboard'))

# View Certificate
@admin_bp.route('/certificate/<int:certificate_id>')
@admin_login_required
def view_certificate(certificate_id):
    certificate = db.session.get(Certificate, certificate_id)
    if not certificate:
        abort(404)
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates'),
        certificate.filename,
        as_attachment=False
    )

# Delete Certificate
@admin_bp.route('/certificate/delete/<int:certificate_id>')
@admin_login_required
def delete_certificate(certificate_id):
    certificate = db.session.get(Certificate, certificate_id)
    if not certificate:
        abort(404)
    
    # Delete file from filesystem
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', certificate.filename))
    except Exception as e:
        flash(f'Error deleting certificate file: {str(e)}', 'warning')
    
    # Delete from database
    db.session.delete(certificate)
    db.session.commit()
    
    flash('Certificate deleted successfully', 'success')
    return redirect(url_for('admin.dashboard'))

# Manage Certifications
@admin_bp.route('/manage-certifications')
@admin_login_required
def manage_certifications():
    # Get search and filter parameters
    search = request.args.get('search', '')
    subject_filter = request.args.get('subject', '')
    difficulty_filter = request.args.get('difficulty', '')
    sort_by = request.args.get('sort', 'title_asc')
    
    # Start with base query for certification courses only
    query = Course.query.filter_by(is_certification=True)
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            db.or_(
                Course.title.ilike(f'%{search}%'),
                Course.description.ilike(f'%{search}%')
            )
        )
    
    # Apply subject filter if provided
    if subject_filter:
        query = query.filter(Course.subject == subject_filter)
    
    # Apply difficulty filter if provided
    if difficulty_filter:
        query = query.filter(Course.difficulty_level == difficulty_filter)
    
    # Apply sorting
    if sort_by == 'title_asc':
        query = query.order_by(Course.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Course.title.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Course.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Course.price.desc())
    
    # Get all certification courses
    certification_courses = query.all()
    
    # Get unique subjects and difficulty levels for filters
    subjects = db.session.query(Course.subject).filter(Course.is_certification == True, Course.subject != None).distinct().all()
    subjects = [subject[0] for subject in subjects if subject[0]]
    
    difficulty_levels = ['Beginner', 'Intermediate', 'Advanced']
    
    return render_template('admin/manage_certifications.html', 
                           certification_courses=certification_courses,
                           subjects=subjects,
                           difficulty_levels=difficulty_levels)

# Edit Certification Course
@admin_bp.route('/edit-certification/<int:course_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_certification(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        abort(404)
    form = CourseForm()
    
    # Populate teacher choices
    teachers = Teacher.query.all()
    form.teacher_id.choices = [(teacher.id, teacher.name) for teacher in teachers]
    
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.price = float(form.price.data)
        course.teacher_id = form.teacher_id.data
        course.is_certification = form.is_certification.data
        course.subject = form.subject.data if form.is_certification.data else None
        course.difficulty_level = form.difficulty_level.data if form.is_certification.data else None
        course.duration = form.duration.data if form.is_certification.data else None
        
        # Update image if a new one is provided
        if form.image.data:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'courses', image_filename))
            course.image = image_filename
        
        db.session.commit()
        flash('Certification course updated successfully!', 'success')
        return redirect(url_for('admin.manage_certifications'))
    
    # Pre-populate form fields
    form.title.data = course.title
    form.description.data = course.description
    form.price.data = str(course.price)
    form.teacher_id.data = course.teacher_id
    form.is_certification.data = course.is_certification
    form.subject.data = course.subject
    form.difficulty_level.data = course.difficulty_level
    form.duration.data = course.duration
    
    return render_template('admin/edit_certification.html', form=form, course=course)

# Delete Certification Course
@admin_bp.route('/delete-certification/<int:course_id>', methods=['POST'])
@admin_login_required
def delete_certification(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        abort(404)
    
    # Check if course has enrolled users
    enrolled_users = UserCourse.query.filter_by(course_id=course.id).all()
    if enrolled_users:
        flash('Cannot delete course. There are users enrolled in this course.', 'danger')
        return redirect(url_for('admin.manage_certifications'))
    
    db.session.delete(course)
    db.session.commit()
    
    flash('Certification course deleted successfully!', 'success')
    return redirect(url_for('admin.manage_certifications'))

# View User
@admin_bp.route('/user/<int:user_id>')
@admin_login_required
def view_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user_courses = UserCourse.query.filter_by(user_id=user.id).all()
    user_certificates = Certificate.query.filter_by(user_id=user.id).all()
    user_orders = Order.query.filter_by(user_id=user.id).all()
    
    return render_template('admin/view_user.html', user=user, user_courses=user_courses, user_certificates=user_certificates, user_orders=user_orders)

# Edit User
@admin_bp.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.view_user', user_id=user.id))
    
    return render_template('admin/edit_user.html', user=user)