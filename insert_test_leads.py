import os
import json
import random
from datetime import datetime, timedelta
from supabase import create_client, Client
from typing import List, Dict

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://xrvxdrsxqnkvbvcrawli.supabase.co')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhydnhkcnN4cW5rdmJ2Y3Jhd2xpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTM0OTg4NywiZXhwIjoyMDcwOTI1ODg3fQ.l_oQ_upWu1kOmlqbWpr-mEdmftsE5ku7DbcfUxfTCMg')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Sample data for generating realistic test leads
FIRST_NAMES = [
    'John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa',
    'James', 'Maria', 'William', 'Jennifer', 'Richard', 'Patricia', 'Charles',
    'Linda', 'Joseph', 'Barbara', 'Thomas', 'Elizabeth', 'Christopher', 'Susan',
    'Daniel', 'Jessica', 'Matthew', 'Karen', 'Anthony', 'Nancy', 'Mark', 'Betty'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
    'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
    'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark',
    'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King'
]

JOB_TITLES = [
    # Operations ICP
    'Operations Manager', 'Plant Manager', 'Production Manager', 'Operations Director',
    'Manufacturing Manager', 'Facility Manager', 'Maintenance Manager', 'Production Engineer',
    'Operations Supervisor', 'Plant Supervisor', 'Manufacturing Engineer', 'Process Engineer',
    'Quality Manager', 'Supply Chain Manager', 'Logistics Manager', 'Operations Analyst',
    
    # Field Service ICP
    'Facility Manager', 'Maintenance Coordinator', 'Service Manager', 'Asset Manager',
    'Property Manager', 'Building Manager', 'Service Coordinator', 'Field Service Manager',
    'Maintenance Supervisor', 'Service Technician Lead', 'Operations Coordinator',
    
    # Non-ICP roles
    'Software Engineer', 'Marketing Manager', 'Sales Representative', 'HR Manager',
    'Financial Analyst', 'Product Manager', 'Business Analyst', 'Customer Success Manager'
]

COMPANIES = [
    # Operations ICP companies
    {'name': 'Advanced Manufacturing Corp', 'industry': 'Manufacturing', 'size': '500-1000', 'founded': 2015},
    {'name': 'Industrial Automation Solutions', 'industry': 'Industrial Automation', 'size': '200-500', 'founded': 2012},
    {'name': 'Precision CNC Systems', 'industry': 'CNC Manufacturing', 'size': '100-200', 'founded': 2010},
    {'name': 'RoboTech Industries', 'industry': 'Robotics', 'size': '1000-5000', 'founded': 2008},
    {'name': 'Heavy Equipment Solutions', 'industry': 'Heavy Equipment', 'size': '500-1000', 'founded': 2005},
    {'name': 'FleetOps Management', 'industry': 'Fleet Operations', 'size': '200-500', 'founded': 2014},
    
    # Field Service ICP companies
    {'name': 'CloudKitchen Express', 'industry': 'Ghost Kitchens', 'size': '50-100', 'founded': 2018},
    {'name': 'Virtual Food Solutions', 'industry': 'Cloud Kitchens', 'size': '100-200', 'founded': 2017},
    {'name': 'Premier Property Management', 'industry': 'Commercial Real Estate', 'size': '200-500', 'founded': 2010},
    {'name': 'Smart Appliance Services', 'industry': 'Managed Appliances', 'size': '100-200', 'founded': 2016},
    {'name': 'Hotel Operations Group', 'industry': 'Hospitality', 'size': '1000-5000', 'founded': 2009},
    {'name': 'Kitchen Automation Pro', 'industry': 'Kitchen Automation', 'size': '50-100', 'founded': 2019},
    
    # Non-ICP companies
    {'name': 'TechStart Solutions', 'industry': 'Software', 'size': '50-100', 'founded': 2020},
    {'name': 'Digital Marketing Agency', 'industry': 'Marketing', 'size': '20-50', 'founded': 2021},
    {'name': 'Financial Services Corp', 'industry': 'Finance', 'size': '500-1000', 'founded': 2000},
    {'name': 'Healthcare Innovations', 'industry': 'Healthcare', 'size': '200-500', 'founded': 2015}
]

LOCATIONS = [
    {'city': 'New York', 'state': 'NY', 'country': 'United States'},
    {'city': 'Los Angeles', 'state': 'CA', 'country': 'United States'},
    {'city': 'Chicago', 'state': 'IL', 'country': 'United States'},
    {'city': 'Houston', 'state': 'TX', 'country': 'United States'},
    {'city': 'Phoenix', 'state': 'AZ', 'country': 'United States'},
    {'city': 'Philadelphia', 'state': 'PA', 'country': 'United States'},
    {'city': 'San Antonio', 'state': 'TX', 'country': 'United States'},
    {'city': 'San Diego', 'state': 'CA', 'country': 'United States'},
    {'city': 'Dallas', 'state': 'TX', 'country': 'United States'},
    {'city': 'San Jose', 'state': 'CA', 'country': 'United States'}
]

EMAIL_STATUSES = ['not_sent', 'sent', 'opened', 'clicked', 'replied', 'bounced']

def calculate_icp_score(job_title: str, company: Dict, location: Dict) -> Dict:
    """Calculate ICP score based on job title, company, and other factors"""
    
    # Initialize scores
    industry_fit = 0
    role_fit = 0
    company_maturity_fit = 0
    decision_maker = 0
    
    # Operations ICP scoring
    operations_industries = ['Manufacturing', 'Industrial Automation', 'CNC Manufacturing', 
                           'Robotics', 'Heavy Equipment', 'Fleet Operations']
    operations_roles = ['Operations Manager', 'Plant Manager', 'Production Manager', 
                       'Operations Director', 'Manufacturing Manager', 'Facility Manager',
                       'Maintenance Manager', 'Production Engineer']
    
    # Field Service ICP scoring
    field_service_industries = ['Ghost Kitchens', 'Cloud Kitchens', 'Commercial Real Estate',
                               'Managed Appliances', 'Hospitality', 'Kitchen Automation']
    field_service_roles = ['Facility Manager', 'Maintenance Coordinator', 'Service Manager',
                          'Asset Manager', 'Property Manager', 'Building Manager']
    
    # Determine ICP category and calculate scores
    icp_category = 'none'
    
    # Check Operations ICP
    if company['industry'] in operations_industries:
        industry_fit = random.randint(7, 10)
        if job_title in operations_roles:
            role_fit = random.randint(8, 10)
            icp_category = 'operations'
        else:
            role_fit = random.randint(2, 5)
    
    # Check Field Service ICP
    elif company['industry'] in field_service_industries:
        industry_fit = random.randint(7, 10)
        if job_title in field_service_roles:
            role_fit = random.randint(8, 10)
            icp_category = 'field_service'
        else:
            role_fit = random.randint(2, 5)
    
    # Non-ICP
    else:
        industry_fit = random.randint(1, 4)
        role_fit = random.randint(1, 4)
    
    # Company maturity scoring
    current_year = datetime.now().year
    company_age = current_year - company['founded']
    if company_age >= 5:
        company_maturity_fit = random.randint(7, 10)
    elif company_age >= 3:
        company_maturity_fit = random.randint(5, 8)
    else:
        company_maturity_fit = random.randint(2, 5)
    
    # Decision maker scoring based on job title
    manager_keywords = ['Manager', 'Director', 'Head', 'Lead', 'Supervisor', 'Chief']
    if any(keyword in job_title for keyword in manager_keywords):
        decision_maker = random.randint(7, 10)
    else:
        decision_maker = random.randint(3, 6)
    
    # Calculate weighted total score
    total_score = (
        industry_fit * 0.3 +
        role_fit * 0.3 +
        company_maturity_fit * 0.2 +
        decision_maker * 0.2
    )
    
    # Determine grade
    if total_score >= 9:
        grade = 'A+'
    elif total_score >= 8:
        grade = 'A'
    elif total_score >= 7:
        grade = 'B+'
    elif total_score >= 6:
        grade = 'B'
    elif total_score >= 5:
        grade = 'C+'
    elif total_score >= 4:
        grade = 'C'
    elif total_score >= 3:
        grade = 'D+'
    else:
        grade = 'D'
    
    return {
        'industry_fit': industry_fit,
        'role_fit': role_fit,
        'company_maturity_fit': company_maturity_fit,
        'decision_maker': decision_maker,
        'total_score': round(total_score, 2),
        'icp_category': icp_category,
        'grade': grade,
        'percentage': round(total_score * 10, 1)
    }

def generate_test_lead(user_id: str = None) -> Dict:
    """Generate a single test lead with realistic data"""
    
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    job_title = random.choice(JOB_TITLES)
    company = random.choice(COMPANIES)
    location = random.choice(LOCATIONS)
    
    # Calculate ICP scoring
    icp_data = calculate_icp_score(job_title, company, location)
    
    # Generate email
    email_domain = company['name'].lower().replace(' ', '').replace('corp', 'corp.com')
    if not email_domain.endswith('.com'):
        email_domain += '.com'
    email = f"{first_name.lower()}.{last_name.lower()}@{email_domain}"
    
    # Generate LinkedIn URL
    linkedin_url = f"https://www.linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(100, 999)}"
    
    # Random dates
    created_date = datetime.now() - timedelta(days=random.randint(1, 90))
    
    lead = {
        'linkedin_url': linkedin_url,
        'full_name': f"{first_name} {last_name}",
        'first_name': first_name,
        'last_name': last_name,
        'headline': f"{job_title} at {company['name']}",
        'about': f"Experienced {job_title.lower()} with expertise in {company['industry'].lower()}. Passionate about operational excellence and continuous improvement.",
        'email': email,
        'email_address': email,
        'email_status': random.choice(EMAIL_STATUSES),
        'job_title': job_title,
        'seniority': 'Manager' if 'Manager' in job_title or 'Director' in job_title else 'Individual Contributor',
        'departments': company['industry'],
        'functions': 'Operations' if 'operations' in icp_data['icp_category'] else 'Field Service' if 'field_service' in icp_data['icp_category'] else 'Other',
        'work_experience_months': random.randint(24, 180),
        'location': f"{location['city']}, {location['state']}",
        'city': location['city'],
        'state': location['state'],
        'country': location['country'],
        'company_name': company['name'],
        'company_industry': company['industry'],
        'company_size': company['size'],
        'company_founded_year': company['founded'],
        'icp_score': icp_data['total_score'],
        'icp_percentage': icp_data['percentage'],
        'icp_grade': icp_data['grade'],
        'icp_breakdown': json.dumps({
            'industry_fit': icp_data['industry_fit'],
            'role_fit': icp_data['role_fit'],
            'company_maturity_fit': icp_data['company_maturity_fit'],
            'decision_maker': icp_data['decision_maker'],
            'icp_category': icp_data['icp_category']
        }),
        'send_email_status': 'Not Sent',
        'scraping_status': 'completed',
        'scraped_at': created_date.isoformat(),
        'created_at': created_date.isoformat(),
        'updated_at': created_date.isoformat()
    }
    
    # user_id is required
    if not user_id:
        raise ValueError("user_id is required for leads")
    lead['user_id'] = user_id
    
    return lead

def get_test_user_id():
    """Get the test user ID"""
    # Use the actual created test user ID
    test_user_id = "c4b6d8f1-ad29-437d-90a3-016a0b4f5331"
    print(f"Using test user ID: {test_user_id}")
    return test_user_id

def insert_test_leads(num_leads: int = 50, user_id: str = None):
    """Insert multiple test leads into the database"""
    
    print(f"Generating {num_leads} test leads...")
    
    leads = []
    for i in range(num_leads):
        lead = generate_test_lead(user_id)
        leads.append(lead)
        
        if (i + 1) % 10 == 0:
            print(f"Generated {i + 1}/{num_leads} leads...")
    
    print("Inserting leads into database...")
    
    try:
        # Insert leads in batches
        batch_size = 10
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]
            result = supabase.table('leads').insert(batch).execute()
            
            if result.data:
                print(f"Successfully inserted batch {i//batch_size + 1} ({len(batch)} leads)")
            else:
                print(f"Error inserting batch {i//batch_size + 1}")
        
        print(f"\n✅ Successfully inserted {num_leads} test leads!")
        
        # Print summary statistics
        print("\n📊 Summary Statistics:")
        icp_categories = {}
        grades = {}
        
        for lead in leads:
            icp_breakdown = json.loads(lead['icp_breakdown'])
            category = icp_breakdown['icp_category']
            grade = lead['icp_grade']
            
            icp_categories[category] = icp_categories.get(category, 0) + 1
            grades[grade] = grades.get(grade, 0) + 1
        
        print("\nICP Categories:")
        for category, count in icp_categories.items():
            print(f"  {category}: {count} leads")
        
        print("\nGrade Distribution:")
        for grade in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D']:
            count = grades.get(grade, 0)
            print(f"  {grade}: {count} leads")
        
        avg_score = sum(lead['icp_score'] for lead in leads) / len(leads)
        print(f"\nAverage ICP Score: {avg_score:.2f}")
        
    except Exception as e:
        print(f"❌ Error inserting leads: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Lead Generation Test Data Script")
    print("===================================\n")
    
    # Verify Supabase connection
    print(f"Connecting to Supabase: {SUPABASE_URL}")
    print("Testing connection...")
    try:
        # Test connection by checking if leads table exists
        result = supabase.table('leads').select('id').limit(1).execute()
        print("✅ Successfully connected to Supabase!")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {str(e)}")
        exit(1)
    
    # Get user input for number of leads
    try:
        num_leads = int(input("Enter number of test leads to generate (default: 50): ") or "50")
        
        if num_leads <= 0:
            print("Number of leads must be positive!")
            exit(1)
        
        # Get test user ID
        print("\n🔧 Using test user...")
        user_id = get_test_user_id()
        
        # Insert test leads
        success = insert_test_leads(num_leads, user_id)
        
        if success:
            print("\n🎉 Test data insertion completed successfully!")
            print("You can now test the ICP functionality with realistic data.")
        else:
            print("\n❌ Test data insertion failed. Please check the errors above.")
            
    except ValueError:
        print("Invalid input. Please enter a valid number.")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")