from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
from models import Category, SubCategory, db, Course, Teacher, Book, BookImage, BookReview, Admin, User, Certificate, UserCourse, Order, OrderItem, Transaction, BundleOffer, FullOrderDetail, Customer, utc_now
from forms import CourseForm, TeacherForm, BookForm, AdminRegistrationForm, AdminLoginForm, CertificateUploadForm, BundleOfferForm
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

# Admin Logout
@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('admin.login'))

# Admin Login
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
        'books': Book.query.filter_by(is_deleted=False).count(),
        'orders': Order.query.count(),
        'bundles': BundleOffer.query.filter_by(is_active=True).count()
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
    
    # Get certificates with enhanced statistics
    recent_certificates = Certificate.query.order_by(Certificate.upload_date.desc()).limit(10).all()
    
    # Enhanced certificate statistics
    stats['certificates'] = Certificate.query.count()
    stats['online_certificates'] = Certificate.query.filter_by(is_offline=False).count()
    stats['offline_certificates'] = Certificate.query.filter_by(is_offline=True).count()
    
    # Recent activity (placeholder data)
    recent_activity = [
        {'text': 'New user registered', 'time': '10 minutes ago', 'icon': 'bi-person-plus', 'color': 'rgba(102, 126, 234, 0.8)'},
        {'text': 'New order placed', 'time': '1 hour ago', 'icon': 'bi-cart-plus', 'color': 'rgba(46, 204, 113, 0.8)'},
        {'text': 'Certificate uploaded', 'time': '3 hours ago', 'icon': 'bi-file-earmark-check', 'color': 'rgba(52, 152, 219, 0.8)'},
        {'text': 'New course added', 'time': '1 day ago', 'icon': 'bi-journal-plus', 'color': 'rgba(155, 89, 182, 0.8)'},
    ]
    
    return render_template('admin/dashboard.html', 
                           admin=admin, 
                           stats=stats, 
                           recent_orders=recent_orders,
                           users=all_users,
                           recent_certificates=recent_certificates,
                           recent_activity=recent_activity)

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



@admin_bp.route('/manage-books')
@admin_login_required
def manage_books():
    search = request.args.get('search', '')
    category_filter = request.args.get('category', type=int)
    sort_by = request.args.get('sort', 'title_asc')

    query = Book.query.filter_by(is_deleted=False)

    if search:
        query = query.filter(
            db.or_(
                Book.title.ilike(f'%{search}%'),
                Book.author.ilike(f'%{search}%'),
                Book.description.ilike(f'%{search}%')
            )
        )

    # ✅ Filter by category
    if category_filter:
        query = query.join(Book.categories).filter(Category.id == category_filter)

    # Sorting
    if sort_by == 'title_asc':
        query = query.order_by(Book.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Book.title.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Book.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Book.price.desc())

    books = query.all()

    # ✅ Get all categories
    categories = Category.query.order_by(Category.name).all()

    return render_template('admin/manage_books.html', books=books, categories=categories)

# Edit Book
@admin_bp.route('/edit-book/<int:book_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    form = BookForm(obj=book)

    # Get all categories and subcategories for the template
    all_categories = Category.query.all()
    all_subcategories = SubCategory.query.all()
    
    # Prepopulate multiple-select fields for GET request
    if request.method == 'GET':
        form.categories.data = [c.id for c in book.categories]
        form.subcategories.data = [sc.id for sc in book.subcategories]

    if form.validate_on_submit():
        # Update book details
        book.title = form.title.data
        book.author = form.author.data
        book.description = form.description.data
        book.price = float(form.price.data)
        book.original_price = float(form.original_price.data) if form.original_price.data else None
        book.quantity = int(form.quantity.data)

        # Update categories and subcategories (many-to-many)
        # Get selected categories from form checkboxes
        selected_category_ids = request.form.getlist('categories')
        selected_category_ids = [int(cat_id) for cat_id in selected_category_ids if cat_id]
        book.categories = Category.query.filter(Category.id.in_(selected_category_ids)).all() if selected_category_ids else []

        # Get selected subcategories from form checkboxes  
        selected_subcategory_ids = request.form.getlist('subcategories')
        selected_subcategory_ids = [int(subcat_id) for subcat_id in selected_subcategory_ids if subcat_id]
        book.subcategories = SubCategory.query.filter(SubCategory.id.in_(selected_subcategory_ids)).all() if selected_subcategory_ids else []

        # Handle image deletions
        delete_images = request.form.getlist('delete_images')
        for image_id in delete_images:
            image = db.session.get(BookImage, image_id)
            if image and image.book_id == book.id:
                # Delete file from filesystem
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', image.image_filename))
                except Exception as e:
                    flash(f'Error deleting image file: {str(e)}', 'warning')
                # Delete from database
                db.session.delete(image)

        # Handle new image uploads
        if form.images.data:
            for image in form.images.data:
                if image.filename:
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'books', filename))
                    book_image = BookImage(image_filename=filename, book_id=book.id)
                    db.session.add(book_image)

        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin.manage_books'))

    return render_template('admin/edit_book.html', form=form, book=book, 
                         all_categories=all_categories, all_subcategories=all_subcategories)

# Delete Book
@admin_bp.route('/delete-book/<int:book_id>')
@admin_login_required
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    try:
        # Soft delete: Mark book as deleted instead of removing from database
        book.is_deleted = True
        book.deleted_at = utc_now()
        
        db.session.commit()
        flash('Book deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_books'))

# Upload Certificate
@admin_bp.route('/upload-certificate', methods=['GET', 'POST'])
@admin_login_required
def upload_certificate():
    form = CertificateUploadForm()
    
    if request.method == 'GET':
        return render_template('admin/upload_certificate.html', form=form)
    
    if form.validate_on_submit():
        # Read selected user from form
        selected_user_id = request.form.get('selected_user')
        if not selected_user_id:
            flash('Please select a user', 'danger')
            return redirect(url_for('admin.upload_certificate'))
        
        try:
            selected_user_id = int(selected_user_id)
        except ValueError:
            flash('Invalid user selection', 'danger')
            return redirect(url_for('admin.upload_certificate'))
        
        # Fetch the selected user
        user = db.session.get(User, selected_user_id)
        if not user:
            flash('Selected user not found', 'danger')
            return redirect(url_for('admin.upload_certificate'))
        
        # Handle offline certificates
        if form.is_offline.data:
            # Save certificate file
            if form.certificate.data:
                # Generate unique filename
                filename = f"{uuid.uuid4().hex}_{secure_filename(form.certificate.data.filename)}"
                certificate_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(certificate_path), exist_ok=True)
                
                try:
                    # Save file
                    form.certificate.data.save(certificate_path)
                    
                    # Create offline certificate record
                    certificate = Certificate(
                        user_id=user.id,
                        course_id=None,
                        filename=filename,
                        upload_date=utc_now(),
                        is_offline=True
                    )
                    db.session.add(certificate)
                    db.session.commit()
                    
                    flash('Offline certificate uploaded successfully', 'success')
                except Exception as e:
                    db.session.rollback()
                    # Clean up saved file on error
                    if os.path.exists(certificate_path):
                        os.remove(certificate_path)
                    flash('Error uploading certificate. Please try again.', 'danger')
            else:
                flash('No certificate file provided', 'danger')
        else:
            # Handle online certificates (existing logic)
            course = db.session.get(Course, form.course_id.data)
            if not course:
                flash('Course not found', 'danger')
                return redirect(url_for('admin.upload_certificate'))
                
            # Check if user is enrolled in the course
            user_course = UserCourse.query.filter_by(user_id=user.id, course_id=course.id).first()
            if not user_course:
                # Create user course enrollment if it doesn't exist
                user_course = UserCourse(user_id=user.id, course_id=course.id, completion_status='completed')
                db.session.add(user_course)
                db.session.commit()
            
            # Save certificate file
            if form.certificate.data:
                # Generate unique filename
                filename = f"{uuid.uuid4().hex}_{secure_filename(form.certificate.data.filename)}"
                certificate_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates', filename)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(certificate_path), exist_ok=True)
                
                try:
                    # Save file
                    form.certificate.data.save(certificate_path)
                    
                    # Create certificate record
                    certificate = Certificate(
                        user_id=user.id,
                        course_id=course.id,
                        filename=filename,
                        upload_date=utc_now(),
                        is_offline=False
                    )
                    db.session.add(certificate)
                    db.session.commit()
                    
                    flash('Certificate uploaded successfully', 'success')
                except Exception as e:
                    db.session.rollback()
                    # Clean up saved file on error
                    if os.path.exists(certificate_path):
                        os.remove(certificate_path)
                    flash('Error uploading certificate. Please try again.', 'danger')
            else:
                flash('No certificate file provided', 'danger')
                
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
                
    return redirect(url_for('admin.upload_certificate'))

def search_users_by_criteria(search_type, search_value):
    """Search users by email or name"""
    if search_type == 'email':
        return User.query.filter(User.email.ilike(f'%{search_value}%')).all()
    elif search_type == 'name':
        # Search in customer table for full_name if available
        customers = Customer.query.filter(Customer.full_name.ilike(f'%{search_value}%')).all()
        user_ids = [c.user_id for c in customers]
        return User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    return []

@admin_bp.route('/search-users', methods=['POST'])
@admin_login_required
def search_users():
    """AJAX endpoint for user search"""
    search_type = request.json.get('search_type')
    search_value = request.json.get('search_value')
    
    users = search_users_by_criteria(search_type, search_value)
    
    return jsonify({
        'users': [{
            'id': user.id,
            'email': user.email,
            'name': user.customer.full_name if user.customer else 'No name available'
        } for user in users]
    })

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

@admin_bp.route('/book-reviews')
@admin_login_required
def manage_book_reviews():
    reviews = BookReview.query.order_by(BookReview.created_at.desc()).all()
    return render_template('admin/manage_reviews.html', reviews=reviews)

@admin_bp.route('/set-book-rating/<int:book_id>', methods=['POST'])
@admin_login_required
def set_book_rating(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)
    
    rating = request.form.get('rating')
    review_count = request.form.get('review_count')
    
    if rating and review_count:
        try:
            book.avg_rating = float(rating)
            book.review_count = int(review_count)
            db.session.commit()
            flash('Book rating updated successfully!', 'success')
        except ValueError:
            flash('Invalid rating or review count values.', 'danger')
    else:
        flash('Rating and review count are required.', 'danger')
    
    return redirect(url_for('admin.edit_book', book_id=book_id))

@admin_bp.route('/book-reviews/delete/<int:review_id>', methods=['POST'])
@admin_login_required
def delete_review(review_id):
    review = db.session.get(BookReview, review_id)
    if not review:
        abort(404)
    
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('admin.manage_book_reviews'))


# Bundle Management Routes

@admin_bp.route('/manage-bundles')
@admin_login_required
def manage_bundles():
    # Search and filter parameters
    search = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'title')
    sort_order = request.args.get('order', 'asc')
    
    # Base query with joined books
    query = BundleOffer.query.options(joinedload(BundleOffer.books))
    
    # Apply search filter (case-insensitive)
    if search:
        query = query.filter(BundleOffer.title.ilike(f'%{search}%'))
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(BundleOffer.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(BundleOffer.is_active == False)
    
    # Apply sorting
    if sort_by == 'title':
        if sort_order == 'desc':
            query = query.order_by(BundleOffer.title.desc())
        else:
            query = query.order_by(BundleOffer.title.asc())
    elif sort_by == 'price':
        if sort_order == 'desc':
            query = query.order_by(BundleOffer.selling_price.desc())
        else:
            query = query.order_by(BundleOffer.selling_price.asc())
    elif sort_by == 'created':
        if sort_order == 'desc':
            query = query.order_by(BundleOffer.created_at.desc())
        else:
            query = query.order_by(BundleOffer.created_at.asc())
    
    bundles = query.all()
    
    return render_template('admin/manage_bundles.html', bundles=bundles, 
                         search=search, status_filter=status_filter, 
                         sort_by=sort_by, sort_order=sort_order)


@admin_bp.route('/add-bundle', methods=['GET', 'POST'])
@admin_login_required
def add_bundle():
    form = BundleOfferForm()
    
    if form.validate_on_submit():
        try:
            # Create new bundle
            bundle = BundleOffer(
                title=form.title.data,
                description=form.description.data,
                mrp=form.mrp.data,
                selling_price=form.selling_price.data,
                discount_type=form.discount_type.data,
                discount_value=form.discount_value.data,
                is_active=form.is_active.data
            )
            
            # Associate selected books
            bundle.books = form.books.data
            
            db.session.add(bundle)
            db.session.commit()
            
            flash('Bundle offer created successfully!', 'success')
            return redirect(url_for('admin.manage_bundles'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating bundle offer. Please try again.', 'error')
    
    return render_template('admin/add_bundle.html', form=form)


@admin_bp.route('/edit-bundle/<int:bundle_id>', methods=['GET', 'POST'])
@admin_login_required
def edit_bundle(bundle_id):
    bundle = db.session.get(BundleOffer, bundle_id)
    if not bundle:
        abort(404)
    
    form = BundleOfferForm(obj=bundle)
    
    if form.validate_on_submit():
        try:
            # Update bundle fields
            bundle.title = form.title.data
            bundle.description = form.description.data
            bundle.mrp = form.mrp.data
            bundle.selling_price = form.selling_price.data
            bundle.discount_type = form.discount_type.data
            bundle.discount_value = form.discount_value.data
            bundle.is_active = form.is_active.data
            
            # Update book associations
            bundle.books = form.books.data
            
            db.session.commit()
            
            flash('Bundle offer updated successfully!', 'success')
            return redirect(url_for('admin.manage_bundles'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating bundle offer. Please try again.', 'error')
    
    # Pre-populate books field
    form.books.data = bundle.books
    
    return render_template('admin/edit_bundle.html', form=form, bundle=bundle)


@admin_bp.route('/delete-bundle/<int:bundle_id>', methods=['POST'])
@admin_login_required
def delete_bundle(bundle_id):
    bundle = db.session.get(BundleOffer, bundle_id)
    if not bundle:
        flash('Bundle not found.', 'error')
        return redirect(url_for('admin.manage_bundles'))
    
    # Safety check: Prevent deletion if bundle is referenced in any orders
    existing_refs = FullOrderDetail.query.filter(
        FullOrderDetail.bundle_id == bundle_id,
        FullOrderDetail.item_type == 'bundle'
    ).first()
    if existing_refs:
        flash('Cannot delete: bundle is referenced by existing orders. Consider deactivating instead.', 'warning')
        return redirect(url_for('admin.manage_bundles'))
    
    try:
        db.session.delete(bundle)
        db.session.commit()
        flash('Bundle offer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting bundle offer. Please try again.', 'error')
    
    return redirect(url_for('admin.manage_bundles'))