from typing import Optional
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, StringField, TextAreaField, FileField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed
from wtforms import StringField, PasswordField, BooleanField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField

from models import Category, SubCategory, Book


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone (Optional)')
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Re-enter Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    terms = BooleanField('I accept the Terms and Conditions', validators=[DataRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class AdminRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Re-enter Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    admin_code = PasswordField('Admin Code', validators=[DataRequired()])
    submit = SubmitField('Register Admin')

class AdminLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CourseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = StringField('Price', validators=[DataRequired()])
    is_certification = BooleanField('Certification Course')
    subject = StringField('Subject')
    difficulty_level = SelectField('Difficulty Level', choices=[
        ('', 'Select Difficulty'),
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced')
    ])
    duration = StringField('Duration (e.g., "4 weeks")')
    teacher_id = SelectField('Teacher', coerce=int, validators=[DataRequired()])
    image = FileField('Course Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Add Course')

class TeacherForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    image = FileField('Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Add Teacher')

def category_choices():
    return Category.query.all()

def subcategory_choices():
    return SubCategory.query.all()

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    description = TextAreaField('Description')
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    original_price = FloatField('Original Price')
    price = FloatField('Price', validators=[DataRequired()])

    categories = QuerySelectMultipleField(
        'Categories', query_factory=category_choices, allow_blank=True, get_label='name'
    )
    subcategories = QuerySelectMultipleField(
        'Subcategories', query_factory=subcategory_choices, allow_blank=True, get_label='name'
    )

    images = MultipleFileField('Upload Images')
    submit = SubmitField('Add Book')

class BookReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '5 Stars - Excellent'),
        ('4', '4 Stars - Very Good'),
        ('3', '3 Stars - Good'),
        ('2', '2 Stars - Fair'),
        ('1', '1 Star - Poor')
    ], validators=[DataRequired()])
    review_text = TextAreaField('Review', validators=[Optional()], render_kw={"rows": 4, "placeholder": "Share your thoughts about this book..."})
    submit = SubmitField('Submit Review')

class CertificateUploadForm(FlaskForm):
    user_search_type = SelectField(
        'Search By',
        choices=[('email', 'Email'), ('name', 'Name')],
        default='email',
        validators=[DataRequired()]
    )
    user_search_value = StringField(
        'User Email/Name',
        validators=[DataRequired(), Length(min=2)],
        render_kw={'placeholder': 'Enter email or name to search'}
    )
    course_id = IntegerField('Course ID (Optional for offline certificates)', validators=[Optional()])
    course_name = StringField('Course Name (Only for offline certificates)', validators=[Optional()])
    is_offline = BooleanField('Offline Certificate', default=False)
    certificate = FileField('Certificate', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF or Images only!')
    ])
    submit = SubmitField('Upload Certificate')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        # If not offline → course_id required
        if not self.is_offline.data and not self.course_id.data:
            self.course_id.errors.append('Course ID is required for online certificates.')
            return False

        # If offline → course_name required
        if self.is_offline.data and not self.course_name.data:
            self.course_name.errors.append('Course Name is required for offline certificates.')
            return False

        return True


class JobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired()])
    description = TextAreaField('Job Description', validators=[DataRequired()])
    location = StringField('Location')
    submit = SubmitField('Post Job')


class JobApplicationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone (Optional)')
    resume = FileField('Upload Resume (PDF)', validators=[
        FileAllowed(['pdf'], 'PDFs only!'), DataRequired()
    ])
    submit = SubmitField('Apply Now')
    
class HeroSliderForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    button_text = StringField('Button Text')
    button_url = StringField('Button URL', default='#')
    image = FileField('PC Image (1920×620)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    mobile_image = FileField('Mobile Image (1440×630)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Save')


class TestimonialForm(FlaskForm):
    name = StringField('Student Name', validators=[DataRequired()])
    role = StringField('Student Role (e.g. Web Development Graduate)', validators=[DataRequired()])
    message = TextAreaField('Testimonial', validators=[DataRequired()])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Submit')    

# Category form
class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired()])
    submit = SubmitField("Save Category")

# SubCategory form
class SubCategoryForm(FlaskForm):
    name = StringField("SubCategory Name", validators=[DataRequired()])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save SubCategory")

# Customer form for detailed address information
class CustomerForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Mobile Number', validators=[DataRequired(), Length(min=10, max=15)])
    street_address = StringField('Street Address', validators=[DataRequired(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state = StringField('State', validators=[DataRequired(), Length(max=100)])
    pincode = StringField('Pincode', validators=[DataRequired(), Regexp(r'^[0-9]{6}$', message='Pincode must be 6 digits')])
    submit = SubmitField('Save Customer Information')


class BundleOfferForm(FlaskForm):
    title = StringField('Bundle Title', validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField('Description', validators=[Optional()], render_kw={'rows': 4})
    mrp = FloatField('MRP (₹)', validators=[DataRequired(), NumberRange(min=0.01, message='MRP must be greater than 0')])
    selling_price = FloatField('Selling Price (₹)', validators=[DataRequired(), NumberRange(min=0.01, message='Selling price must be greater than 0')])
    discount_type = SelectField('Discount Type', choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')], validators=[DataRequired()])
    discount_value = FloatField('Discount Value', validators=[DataRequired(), NumberRange(min=0, message='Discount value cannot be negative')])
    books = QuerySelectMultipleField('Select Books', query_factory=lambda: Book.query.filter_by(is_deleted=False).all(), allow_blank=False, get_label='title')
    is_active = BooleanField('Active Bundle', default=True)
    submit = SubmitField('Save Bundle Offer')

    def validate_selling_price(self, field):
        if self.mrp.data and field.data and field.data >= self.mrp.data:
            raise ValidationError('Selling price must be less than MRP')
    
    def validate_discount_value(self, field):
        if self.mrp.data and self.selling_price.data and field.data:
            if self.discount_type.data == 'percentage':
                if field.data >= 100:
                    raise ValidationError('Percentage discount must be less than 100%')
                expected_price = self.mrp.data * (1 - field.data/100)
                if abs(expected_price - self.selling_price.data) > 0.01:
                    raise ValidationError('Discount percentage does not match the price difference')
            elif self.discount_type.data == 'fixed':
                if field.data >= self.mrp.data:
                    raise ValidationError('Fixed discount cannot be greater than or equal to MRP')
                expected_price = self.mrp.data - field.data
                if abs(expected_price - self.selling_price.data) > 0.01:
                    raise ValidationError('Fixed discount does not match the price difference')

    def validate_books(self, field):
        if not field.data or len(field.data) == 0:
            raise ValidationError('Please select at least one book for the bundle.')