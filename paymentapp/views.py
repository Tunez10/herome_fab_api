# paymentapp/views.py
import requests
import uuid
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.models import Order
from .utils import send_transaction_emails, send_payment_confirmation_email

PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"

class InitiatePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        email = user.email
        username = user.username
        amount = request.data.get("amount")
        metadata = request.data.get("metadata", {}) 

        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        reference = str(uuid.uuid4()).replace("-", "")[:12]
        amount_kobo = int(Decimal(amount) * 100)

        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email, 
            "amount": amount_kobo, 
            "reference": reference,
            "callback_url": f"{settings.FRONTEND_URL}/verify-payment?reference={reference}",
            "metadata": metadata
            }

        response = requests.post(PAYSTACK_INITIALIZE_URL, headers=headers, data=data)
        res_data = response.json()

        if res_data.get("status") is True:
            # Send email to admin and user
            admin_email = settings.DEFAULT_FROM_EMAIL
            try:
                send_transaction_emails(
                    admin_email,
                    email,
                    reference,
                    amount,
                    username,
                )
            except Exception as e:
                print(f"Error sending admin email: {e}")

            # Return the authorization URL and reference to frontend
            return Response(
                {
                    "authorization_url": res_data["data"]["authorization_url"],
                    "reference": reference
                },
                status=status.HTTP_200_OK
            )

        return Response({"error": res_data.get("message", "Payment initialization failed")}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reference = request.query_params.get("reference")
        if not reference:
            return Response({"success": False, "message": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)

        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        response = requests.get(PAYSTACK_VERIFY_URL.format(reference), headers=headers)
        res_data = response.json()

        if res_data.get("status") and res_data["data"]["status"] == "success":
            amount = Decimal(res_data["data"]["amount"]) / 100
            user = request.user
            metadata = res_data["data"].get("metadata") or {}

            # Create Order after verification
            order = Order.objects.create(
                user=user,
                reference=reference,
                amount=amount,
                status="paid",
                confirm_status="pending",
                metadata=metadata
            )

            # Send payment confirmation email to user
            try:
                send_payment_confirmation_email(user.email, reference, amount, user.username)
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

            # Return success for frontend automatic redirect
            return Response({
                "success": True,
                "redirect_url": f"/payment-success?reference={reference}"
            }, status=status.HTTP_200_OK)

        # Payment failed
        return Response({
            "success": False,
            "redirect_url": "/payment-failed"
        }, status=status.HTTP_200_OK)
