#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.lead_service import LeadService

async def test_add_lead():
    """Test adding a sample lead to the database"""
    
    # Initialize the lead service
    lead_service = LeadService()
    
    # Create a sample lead
    sample_lead = {
        "full_name": "John Smith",
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@testmfg.com",
        "job_title": "Operations Manager",
        "company_name": "Test Manufacturing Corp",
        "company_industry": "Manufacturing",
        "company_size": "201-500",
        "location": "Texas, USA",
        "city": "Dallas",
        "state": "Texas",
        "country": "USA",
        "phone_number": "+1-555-0123",
        "linkedin_url": "https://linkedin.com/in/johnsmith",
        "icp_score": 85.0,
        "icp_percentage": 85.0,
        "icp_grade": "A",
        "email_status": "Not Verified",
        "send_email_status": "Not Sent",
        "scraping_status": "Completed"
    }
    
    try:
        # Save the lead to the database
        result = await lead_service._save_leads_to_db([sample_lead])
        print(f"Result: {result}")
        
        # Test retrieving leads
        leads_result = await lead_service.get_leads(limit=5)
        print(f"\nRetrieved leads: {leads_result}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_add_lead())