# mock_gcash.py - SIMPLE WORKING VERSION
import uuid
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict

class MockGCashAPI:
    """Simple Mock GCash API"""
    
    def __init__(self):
        self.payments = {}
    
    def create_payment(self, order_data: Dict) -> Dict:
        """Create a mock payment"""
        transaction_id = f"mock_txn_{int(time.time())}_{random.randint(1000, 9999)}"
        reference_number = f"MOCK_REF_{order_data.get('order_id', 0)}_{int(time.time())}"
        
        # Calculate expiry
        expires_at = datetime.now() + timedelta(minutes=30)
        
        # Store payment
        self.payments[transaction_id] = {
            "order_id": order_data.get("order_id"),
            "amount": order_data.get("amount", 0),
            "customer_name": order_data.get("customer_name", ""),
            "customer_phone": order_data.get("customer_phone", ""),
            "status": "PENDING",
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "paid": False
        }
        
        # Generate checkout URL
        checkout_url = f"/api/mock-gcash/pay/{transaction_id}"
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "checkout_url": checkout_url,
            "reference_number": reference_number,
            "expires_at": expires_at.isoformat(),
            "amount": order_data.get("amount", 0),
            "merchant_code": "MOCK_MERCHANT_001",
            "message": "Mock GCash payment created successfully"
        }
    
    def simulate_payment(self, transaction_id: str, success: bool = True) -> Dict:
        """Simulate payment"""
        if transaction_id not in self.payments:
            return {"error": "Transaction not found"}
        
        payment = self.payments[transaction_id]
        
        if success:
            payment["status"] = "SUCCESS"
            payment["paid"] = True
            payment["paid_at"] = datetime.now()
        else:
            payment["status"] = "FAILED"
            payment["paid"] = False
        
        return {"success": True, "status": payment["status"]}
    
    def check_payment_status(self, transaction_id: str) -> Dict:
        """Check payment status"""
        payment = self.payments.get(transaction_id)
        
        if not payment:
            return {
                "success": False,
                "status": "NOT_FOUND",
                "paid": False
            }
        
        return {
            "success": True,
            "status": payment["status"],
            "paid": payment["paid"],
            "transaction_id": transaction_id,
            "amount": payment["amount"],
            "paid_at": payment.get("paid_at"),
            "expires_at": payment.get("expires_at")
        }
    
    def get_all_payments(self):
        """Get all payments"""
        return self.payments
    
    def reset_payments(self):
        """Reset all payments"""
        self.payments.clear()
        return {"success": True, "message": "All mock payments cleared"}

# Create instance
mock_gcash = MockGCashAPI()
