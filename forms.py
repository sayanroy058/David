from typing import Optional
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, StringField, TextAreaField, FileField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed
from wtforms import StringField, PasswordField, BooleanField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

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

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    category = StringField('Category', validators=[Optional()])
    subject = StringField('Subject', validators=[Optional()])
    quantity = IntegerField('Quantity', default=1)
    original_price = FloatField('Original Price', validators=[Optional()])
    price = FloatField('Selling Price', default=0.0)
    images = MultipleFileField('Upload Book Images (JPG, PNG)', validators=[Optional()])
    submit = SubmitField('Add Book')

class CertificateUploadForm(FlaskForm):
    user_email = SelectField('User Email', validators=[DataRequired()], coerce=str)
    course_id = StringField('Course ID', validators=[DataRequired()])
    certificate = FileField('Certificate', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF or Images only!')
    ])
    submit = SubmitField('Upload Certificate')

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
    image = FileField('Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Save')


class TestimonialForm(FlaskForm):
    name = StringField('Student Name', validators=[DataRequired()])
    role = StringField('Student Role (e.g. Web Development Graduate)', validators=[DataRequired()])
    message = TextAreaField('Testimonial', validators=[DataRequired()])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Submit')    

class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired()])
    submit = SubmitField("Add Category")

class SubCategoryForm(FlaskForm):
    name = StringField("Subcategory Name", validators=[DataRequired()])
    category_id = SelectField("Parent Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Add Subcategory")