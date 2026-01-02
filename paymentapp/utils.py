# paymentapp/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime

def render_email_body(title, body):
    """Helper to wrap dynamic body in your master email template"""
    context = {
        "logo_url": f"{settings.FRONTEND_URL}/static/logo.png" if hasattr(settings, 'FRONTEND_URL') else "",
        "year": datetime.now().year,
        "body_content": f"<h3>{title}</h3><p>{body}</p>"
    }
    return render_to_string('email_template.html', context)


def send_transaction_emails(admin_email, customer_email, reference, amount, username):
    """Send email to admin + user when payment is initiated"""
    # ---- Email to Admin ----
    subject_admin = f"New Payment Attempt - {reference}"
    admin_body = render_email_body(
        "Payment Attempt Notification",
        f"User <strong>{username}</strong> just initiated a payment of <span class='highlight'>₦{amount}</span>.<br>Reference: <strong>{reference}</strong>."
    )
    admin_msg = EmailMultiAlternatives(subject_admin, strip_tags(admin_body), settings.DEFAULT_FROM_EMAIL, [admin_email])
    admin_msg.attach_alternative(admin_body, "text/html")
    admin_msg.send()

    # ---- Email to User ----
    subject_user = f"Payment Initiated - {reference}"
    user_body = render_email_body(
        "Your Payment is Being Processed",
        f"Hi <strong>{username}</strong>,<br>We’ve received your payment attempt of <span class='highlight'>₦{amount}</span>.<br>We’ll confirm once it’s verified.<br>Reference: <strong>{reference}</strong>."
    )
    user_msg = EmailMultiAlternatives(subject_user, strip_tags(user_body), settings.DEFAULT_FROM_EMAIL, [customer_email])
    user_msg.attach_alternative(user_body, "text/html")
    user_msg.send()


def send_payment_confirmation_email(customer_email, reference, amount, username):
    """Send confirmation email after payment verification"""
    subject = f"Payment Confirmed - {reference}"
    body = render_email_body(
        "Payment Successful",
        f"Hi <strong>{username}</strong>,<br>Your payment of <span class='highlight'>₦{amount}</span> has been confirmed.<br>Your order is now being processed.<br>Thank you for shopping with <strong>Herome_Fab</strong>!"
    )
    msg = EmailMultiAlternatives(subject, strip_tags(body), settings.DEFAULT_FROM_EMAIL, [customer_email])
    msg.attach_alternative(body, "text/html")
    msg.send()
