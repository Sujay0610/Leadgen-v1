import requests
import json
from datetime import datetime

def send_test_webhook(event_type):
    webhook_url = "https://resend-backend-f6tv.onrender.com/resend-webhook"
    
    # Base webhook data
    webhook_data = {
        "type": event_type,
        "created_at": datetime.utcnow().isoformat(),
        "data": {
            "email_id": "test-email-123",
            "from": "test@example.com",
            "to": ["recipient@example.com"],
            "subject": "Test Email",
            "tags": ["test"]
        }
    }
    
    # Add event-specific data
    if event_type == "email.bounced":
        webhook_data["data"]["bounce"] = {
            "type": "hard",
            "subType": "invalid_recipient",
            "message": "Invalid recipient"
        }
    elif event_type == "email.clicked":
        webhook_data["data"]["click"] = {
            "ipAddress": "127.0.0.1",
            "link": "https://example.com",
            "userAgent": "Mozilla/5.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    elif event_type == "email.opened":
        webhook_data["data"]["device_info"] = {
            "type": "desktop",
            "os": "Windows"
        }
        webhook_data["data"]["location_info"] = {
            "city": "Test City",
            "country": "Test Country"
        }
    
    # Send the webhook
    response = requests.post(
        webhook_url,
        json=webhook_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nSent {event_type} webhook:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def main():
    # Test different event types
    event_types = [
        "email.sent",
        "email.delivered",
        "email.opened",
        "email.clicked",
        "email.bounced"
    ]
    
    for event_type in event_types:
        send_test_webhook(event_type)
        input(f"\nPress Enter to send next webhook ({event_type})...")

if __name__ == "__main__":
    main() 