"""
Sends the drafted follow-up email using Gmail's SMTP server.

This uses an "App Password" (not your real Gmail password) — a
16-character code Google generates specifically for apps like this,
so you never expose your actual account password in code.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(recipients: List[str], subject: str, body: str):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise ValueError("GMAIL_ADDRESS or GMAIL_APP_PASSWORD is not set in your .env file")

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # upgrades the connection to a secure encrypted one
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
