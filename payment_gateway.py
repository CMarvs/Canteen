"""
Payment Gateway Integration Module
Supports GCash via PayMongo (Philippines payment gateway)
and Direct GCash-to-GCash payments
"""

import os
import requests
import base64
import json
import qrcode
import io
from typing import Dict, Optional
from PIL import Image

# PayMongo API Configuration
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY", "")
PAYMONGO_PUBLIC_KEY = os.getenv("PAYMONGO_PUBLIC_KEY", "")
PAYMONGO_API_URL = "https://api.paymongo.com/v1"

# GCash Direct API (if you have access)
GCASH_API_KEY = os.getenv("GCASH_API_KEY", "")
GCASH_SECRET_KEY = os.getenv("GCASH_SECRET_KEY", "")
GCASH_API_URL = os.getenv("GCASH_API_URL", "https://api.gcash.com")

# Admin GCash Number (for direct transfers)
ADMIN_GCASH_NUMBER = os.getenv("ADMIN_GCASH_NUMBER", "09947784922")

def get_paymongo_auth_header() -> str:
    """Generate PayMongo authentication header"""
    if not PAYMONGO_SECRET_KEY:
        raise ValueError("PAYMONGO_SECRET_KEY not set in environment variables")
    
    # PayMongo uses Basic Auth with secret key
    credentials = f"{PAYMONGO_SECRET_KEY}:"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def process_gcash_payment_paymongo(order_id: int, amount: float, gcash_number: str, order_details: Dict) -> Dict:
    """
    Process GCash payment via PayMongo
    
    Args:
        order_id: Order ID
        amount: Payment amount in PHP
        gcash_number: GCash mobile number (11 digits)
        order_details: Additional order information
    
    Returns:
        Dict with payment result
    """
    try:
        # Step 1: Create Payment Intent
        payment_intent_data = {
            "data": {
                "attributes": {
                    "amount": int(amount * 100),  # Convert to centavos
                    "currency": "PHP",
                    "payment_method_allowed": ["gcash"],
                    "description": f"Order #{order_id} - RMLCanteen",
                    "metadata": {
                        "order_id": str(order_id),
                        "customer_name": order_details.get("customer_name", ""),
                        "customer_contact": order_details.get("customer_contact", "")
                    }
                }
            }
        }
        
        headers = {
            "Authorization": get_paymongo_auth_header(),
            "Content-Type": "application/json"
        }
        
        # Create payment intent
        response = requests.post(
            f"{PAYMONGO_API_URL}/payment_intents",
            headers=headers,
            json=payment_intent_data,
            timeout=30
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("detail", "Payment intent creation failed")
            raise Exception(f"PayMongo API Error: {error_msg}")
        
        payment_intent = response.json()
        client_key = payment_intent["data"]["attributes"]["client_key"]
        payment_intent_id = payment_intent["data"]["id"]
        
        # Step 2: Attach Payment Method (GCash)
        payment_method_data = {
            "data": {
                "attributes": {
                    "type": "gcash",
                    "billing": {
                        "name": order_details.get("customer_name", ""),
                        "phone": gcash_number,
                        "email": order_details.get("customer_email", "")
                    },
                    "metadata": {
                        "order_id": str(order_id)
                    }
                }
            }
        }
        
        # Attach payment method
        method_response = requests.post(
            f"{PAYMONGO_API_URL}/payment_methods",
            headers=headers,
            json=payment_method_data,
            timeout=30
        )
        
        if method_response.status_code != 200:
            error_data = method_response.json() if method_response.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("detail", "Payment method attachment failed")
            raise Exception(f"PayMongo API Error: {error_msg}")
        
        payment_method = method_response.json()
        payment_method_id = payment_method["data"]["id"]
        
        # Step 3: Attach payment method to payment intent
        attach_data = {
            "data": {
                "attributes": {
                    "payment_method": payment_method_id,
                    "return_url": order_details.get("return_url", "https://your-app.onrender.com/orders.html")
                }
            }
        }
        
        attach_response = requests.post(
            f"{PAYMONGO_API_URL}/payment_intents/{payment_intent_id}/attach",
            headers=headers,
            json=attach_data,
            timeout=30
        )
        
        if attach_response.status_code != 200:
            error_data = attach_response.json() if attach_response.text else {}
            error_msg = error_data.get("errors", [{}])[0].get("detail", "Payment attachment failed")
            raise Exception(f"PayMongo API Error: {error_msg}")
        
        result = attach_response.json()
        status = result["data"]["attributes"]["status"]
        
        # Check payment status
        if status == "succeeded":
            return {
                "success": True,
                "message": "GCash payment processed successfully",
                "payment_intent_id": payment_intent_id,
                "payment_method_id": payment_method_id,
                "status": "paid"
            }
        elif status == "awaiting_payment_method" or status == "awaiting_next_action":
            # Payment requires user action (redirect to GCash)
            next_action = result["data"]["attributes"].get("next_action", {})
            redirect_url = next_action.get("redirect", {}).get("url", "")
            
            return {
                "success": False,
                "requires_action": True,
                "message": "Please complete payment in GCash app",
                "redirect_url": redirect_url,
                "payment_intent_id": payment_intent_id,
                "status": "pending"
            }
        else:
            return {
                "success": False,
                "message": f"Payment status: {status}",
                "status": "pending"
            }
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to PayMongo: {str(e)}")
    except Exception as e:
        raise Exception(f"GCash payment processing failed: {str(e)}")

def check_payment_status_paymongo(payment_intent_id: str) -> Dict:
    """
    Check payment status from PayMongo
    
    Args:
        payment_intent_id: PayMongo payment intent ID
    
    Returns:
        Dict with payment status
    """
    try:
        headers = {
            "Authorization": get_paymongo_auth_header(),
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{PAYMONGO_API_URL}/payment_intents/{payment_intent_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception("Failed to check payment status")
        
        data = response.json()
        status = data["data"]["attributes"]["status"]
        
        return {
            "status": status,
            "paid": status == "succeeded",
            "pending": status in ["awaiting_payment_method", "awaiting_next_action"],
            "failed": status == "failed"
        }
        
    except Exception as e:
        raise Exception(f"Failed to check payment status: {str(e)}")

def process_gcash_direct(order_id: int, amount: float, gcash_number: str, order_details: Dict) -> Dict:
    """
    Process GCash payment via direct GCash API (if you have access)
    
    Note: This requires GCash Business API access which is limited to partners.
    Contact GCash for API access.
    """
    if not GCASH_API_KEY or not GCASH_SECRET_KEY:
        raise Exception("GCash API credentials not configured. Please contact GCash for Business API access.")
    
    try:
        # Generate access token (OAuth 2.0)
        auth_response = requests.post(
            f"{GCASH_API_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": GCASH_API_KEY,
                "client_secret": GCASH_SECRET_KEY
            },
            timeout=30
        )
        
        if auth_response.status_code != 200:
            raise Exception("Failed to authenticate with GCash API")
        
        access_token = auth_response.json().get("access_token")
        
        # Create payment request
        payment_data = {
            "amount": amount,
            "currency": "PHP",
            "mobile_number": gcash_number,
            "description": f"Order #{order_id} - RMLCanteen",
            "reference_number": f"ORDER_{order_id}",
            "callback_url": order_details.get("callback_url", ""),
            "metadata": {
                "order_id": str(order_id)
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{GCASH_API_URL}/payments",
            headers=headers,
            json=payment_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": "GCash payment request sent. Please confirm in your GCash app.",
                "payment_id": result.get("payment_id"),
                "status": "pending"
            }
        else:
            error_data = response.json() if response.text else {}
            raise Exception(error_data.get("message", "GCash payment request failed"))
            
    except Exception as e:
        raise Exception(f"GCash direct API error: {str(e)}")

def generate_gcash_qr_code(amount: float, reference: str, admin_number: str) -> str:
    """
    Generate GCash QR code data for payment
    Format: GCash payment string with admin number, amount, and reference
    """
    # Format: Send to admin number with amount and reference
    # This creates a payment instruction that can be scanned
    qr_data = f"Send ₱{amount:.2f} to {admin_number}\nReference: {reference}"
    return qr_data

def generate_gcash_qr_image(qr_data: str) -> bytes:
    """
    Generate QR code image as bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def generate_gcash_payment_link(amount: float, reference: str, admin_number: str) -> Dict:
    """
    Generate GCash payment request/link
    Returns payment instructions and QR code data
    """
    qr_data = generate_gcash_qr_code(amount, reference, admin_number)
    
    return {
        "success": True,
        "payment_type": "direct_gcash",
        "admin_gcash_number": admin_number,
        "amount": amount,
        "reference": reference,
        "qr_data": qr_data,
        "instructions": f"Send ₱{amount:.2f} to GCash number {admin_number}\nReference: {reference}\n\nPlease send the payment and keep your reference number for verification.",
        "status": "pending"
    }

def process_gcash_direct_transfer(order_id: int, amount: float, customer_gcash: str, admin_gcash: str, order_details: Dict) -> Dict:
    """
    Process direct GCash-to-GCash transfer
    Generates payment request with QR code
    """
    reference = f"ORDER_{order_id}_{int(os.urandom(4).hex(), 16)}"
    
    payment_info = generate_gcash_payment_link(
        amount=amount,
        reference=reference,
        admin_number=admin_gcash
    )
    
    payment_info["order_id"] = order_id
    payment_info["customer_gcash"] = customer_gcash
    payment_info["payment_intent_id"] = reference  # Use reference as payment ID
    
    return payment_info

def process_gcash_payment(order_id: int, amount: float, gcash_number: str, order_details: Dict, use_paymongo: bool = True, use_direct: bool = False) -> Dict:
    """
    Main function to process GCash payment
    
    Args:
        order_id: Order ID
        amount: Payment amount
        gcash_number: GCash mobile number
        order_details: Order information
        use_paymongo: Use PayMongo gateway (True) or direct GCash API (False)
        use_direct: Use direct GCash-to-GCash transfer (True)
    
    Returns:
        Payment result dictionary
    """
    # Direct GCash-to-GCash transfer (preferred if admin number is set)
    if use_direct or ADMIN_GCASH_NUMBER:
        return process_gcash_direct_transfer(
            order_id=order_id,
            amount=amount,
            customer_gcash=gcash_number,
            admin_gcash=ADMIN_GCASH_NUMBER,
            order_details=order_details
        )
    
    # PayMongo integration (alternative)
    if use_paymongo:
        if not PAYMONGO_SECRET_KEY:
            # Fallback to direct transfer if PayMongo not configured
            return process_gcash_direct_transfer(
                order_id=order_id,
                amount=amount,
                customer_gcash=gcash_number,
                admin_gcash=ADMIN_GCASH_NUMBER,
                order_details=order_details
            )
        return process_gcash_payment_paymongo(order_id, amount, gcash_number, order_details)
    else:
        return process_gcash_direct(order_id, amount, gcash_number, order_details)

