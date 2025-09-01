#!/usr/bin/env python3
"""
Script to get a test authentication token for API testing
"""

import os
import sys
from supabase import create_client, Client
from config import get_settings

def get_test_token():
    """Get authentication token for test user"""
    try:
        settings = get_settings()
        
        # Create Supabase client
        supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Test user credentials
        email = "test@example.com"
        password = "testpassword123"
        
        print(f"Attempting to sign in with {email}...")
        
        # Sign in
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.session and response.session.access_token:
            print("\n✅ Authentication successful!")
            print(f"\n🔑 Access Token:")
            print(response.session.access_token)
            print(f"\n👤 User ID: {response.user.id}")
            print(f"📧 Email: {response.user.email}")
            
            # Test the token with backend
            print("\n🧪 Testing token with backend...")
            import requests
            
            headers = {
                'Authorization': f'Bearer {response.session.access_token}',
                'Content-Type': 'application/json'
            }
            
            try:
                test_response = requests.get('http://localhost:8000/protected', headers=headers)
                if test_response.status_code == 200:
                    print("✅ Token validation successful!")
                    print(f"Response: {test_response.json()}")
                else:
                    print(f"❌ Token validation failed: {test_response.status_code}")
                    print(f"Response: {test_response.text}")
            except Exception as e:
                print(f"❌ Error testing token: {e}")
            
            return response.session.access_token
        else:
            print("❌ Authentication failed - no session or token")
            print(f"Response: {response}")
            return None
            
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return None

if __name__ == "__main__":
    # Add backend directory to path
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    sys.path.insert(0, backend_path)
    
    # Change to backend directory
    os.chdir(backend_path)
    
    token = get_test_token()
    if token:
        print(f"\n🎯 Use this token for API testing:")
        print(f"Authorization: Bearer {token}")
    else:
        print("\n❌ Failed to get authentication token")
        sys.exit(1)