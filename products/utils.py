from django.utils.text import slugify

# productapp/utils.py
from django.core.mail import send_mail
from django.conf import settings

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime

def generate_unique_slug(model_class, name):
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug






def send_transaction_emails(admin_email, customer_email, context):
    # ✅ Logo and year
    logo_url = f"{settings.SITE_URL}/static/images/heromefab.jpg"
    year = datetime.now().year

    # ✅ ADMIN EMAIL
    admin_html = render_to_string("email_template.html", {
        "logo_url": logo_url,
        "year": year,
        "body_content": f"""
            <h2>New Payment Received</h2>
            <p>Hello Admin,</p>
            <p>You have received a new payment from <b>{context['customer_name']}</b>.</p>
            <p><b>Product(s):</b> {context['product_names']}<br>
            <b>Amount:</b> ₦{context['amount']}<br>
            <b>Transaction Reference:</b> {context['reference']}</p>
            <p>Login to your dashboard to confirm payment.</p>
        """
    })
    admin_text = strip_tags(admin_html)

    msg_admin = EmailMultiAlternatives(
        subject=f"New Payment Received - {context['reference']}",
        body=admin_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email],
    )
    msg_admin.attach_alternative(admin_html, "text/html")
    msg_admin.send(fail_silently=False)

    # ✅ CUSTOMER EMAIL
    customer_html = render_to_string("email_template.html", {
        "logo_url": logo_url,
        "year": year,
        "body_content": f"""
            <h2>Payment Initiated</h2>
            <p>Hi {context['customer_name']},</p>
            <p>Your payment of ₦{context['amount']} for <b>{context['product_names']}</b> has been acknowledged.</p>
            <p>Please wait while we confirm your payment. Thank you for shopping with <span class="highlight">Herome_Fab</span>!</p>
            <p><b>Transaction Reference:</b> {context['reference']}</p>
        """
    })
    customer_text = strip_tags(customer_html)

    msg_customer = EmailMultiAlternatives(
        subject=f"Payment Received - Reference {context['reference']}",
        body=customer_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer_email],
    )
    msg_customer.attach_alternative(customer_html, "text/html")
    msg_customer.send(fail_silently=False)



