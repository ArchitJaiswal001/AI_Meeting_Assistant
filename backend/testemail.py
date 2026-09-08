"""
Quick standalone test — run this BEFORE testing the full app, to confirm
your Gmail App Password is working correctly.

Usage:
    cd backend
    python test_email.py
"""
from services.emailer import send_email

# Change this to your own email so you can check your inbox
TEST_RECIPIENT = "youractualemail@gmail.com"

if __name__ == "__main__":
    try:
        send_email(
            recipients=[TEST_RECIPIENT],
            subject="Test email from AI Meeting Assistant",
            body="If you're reading this, your Gmail SMTP setup works correctly!",
        )
        print("✅ Success! Check your inbox at:", TEST_RECIPIENT)
    except Exception as e:
        print("❌ Failed:", e)