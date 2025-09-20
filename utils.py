import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Email configuration
# For Gmail, you need to:
# 1. Enable 2-Step Verification in your Google account
# 2. Generate an App Password: Google Account > Security > App Passwords
# 3. Use that App Password here instead of your regular password
EMAIL_ADDRESS = "easy2learning2020@gmail.com"
EMAIL_PASSWORD = "doux wlaf nmaj skwu"  # Replace with actual App Password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Set this to False to disable actual email sending (for testing)
ENABLE_EMAIL_SENDING = True

def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))

def send_reset_email(user_email, otp):
    """Send password reset email with OTP"""
    # If email sending is disabled, just log and return success
    if not ENABLE_EMAIL_SENDING:
        print(f"[TEST MODE] Would send OTP {otp} to {user_email}")
        return True
        
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Password Reset - Easy2Learning"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = user_email
        
        # Create the body of the message
        html = f"""
        <html>
          <head></head>
          <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
              <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #333333;">Easy2Learning Password Reset</h2>
              </div>
              <p>Hello,</p>
              <p>We received a request to reset your password. Please use the following One-Time Password (OTP) to complete the process:</p>
              <div style="text-align: center; margin: 30px 0;">
                <div style="font-size: 24px; font-weight: bold; letter-spacing: 5px; padding: 10px; background-color: #f5f5f5; border-radius: 5px; display: inline-block;">{otp}</div>
              </div>
              <p>This OTP is valid for 15 minutes. If you did not request a password reset, please ignore this email.</p>
              <p>Thank you,<br>Easy2Learning Team</p>
            </div>
          </body>
        </html>
        """
        
        # Record the MIME type
        part = MIMEText(html, 'html')
        
        # Attach parts into message container
        msg.attach(part)
        
        # Send the message via SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        
        # Detailed error handling for login
        try:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        except smtplib.SMTPAuthenticationError as auth_error:
            print(f"SMTP Authentication Error: {auth_error}")
            print("Please check your email and App Password settings.")
            print("For Gmail, you need to use an App Password if 2FA is enabled.")
            server.quit()
            return False
        
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False