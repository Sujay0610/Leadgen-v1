import asyncio
import json
from services.lead_service import LeadService

# Sample lead data from the API response
sample_lead = {
    "linkedin_url": "http://www.linkedin.com/in/akarpiak",
    "fullName": "Adam Karpiak",
    "firstName": "Adam",
    "lastName": "Karpiak",
    "jobTitle": "Co-Founder",
    "email": "akarpiak@karpiakconsulting.com",
    "email_status": "verified",
    "photo_url": "https://media.licdn.com/dms/image/v2/D4E03AQHnuftDhTf6mA/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1683652621982?e=2147483647&v=beta&t=vTHPUjRncTAUFrQbkdnokdJrTOhVnrlpkph5S5cIImQ",
    "headline": "I help people get hired with better resumes, smarter strategies, & no BS. It's hard to play the game if you don't know the rules.",
    "location": "United States",
    "city": "",
    "state": "",
    "country": "United States",
    "seniority": "founder",
    "departments": [],
    "subdepartments": [],
    "functions": [],
    "work_experience_months": 270,
    "employment_history": [],
    "intent_strength": "",
    "show_intent": True,
    "email_domain_catchall": False,
    "revealed_for_current_team": True,
    "companyName": "Karpiak Consulting",
    "companyWebsite": "http://www.karpiakconsulting.com",
    "companyLinkedIn": "http://www.linkedin.com/company/karpiak-consulting-llc",
    "companyTwitter": "",
    "companyFacebook": "",
    "companyPhone": "+1 646-837-5750",
    "companyFoundedYear": 2011,
    "companySize": "",
    "companyIndustry": "",
    "companyDomain": "karpiakconsulting.com",
    "companyGrowth6Month": 0,
    "companyGrowth12Month": 0,
    "companyGrowth24Month": 0,
    "send_email_status": "Not Sent",
    "icp_score": 32.0,
    "icp_grade": "C",
    "icp_breakdown": {}
}

async def test_single_lead_insert():
    """Test inserting a single lead to verify database functionality"""
    try:
        print("Testing single lead insertion...")
        print(f"Lead data: {json.dumps(sample_lead, indent=2)}")
        
        # Initialize lead service
        lead_service = LeadService()
        
        # Test the save function with a single lead
        result = await lead_service._save_leads_to_db([sample_lead])
        
        print("\n=== INSERTION RESULT ===")
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        print(f"Save Stats: {json.dumps(result.get('save_stats', {}), indent=2)}")
        
        if result.get('status') == 'success':
            print("✅ Lead insertion successful!")
        else:
            print("❌ Lead insertion failed!")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_lead_insert())