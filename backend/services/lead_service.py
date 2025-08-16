import asyncio
import re
import os
import uuid
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
import time
import requests
from supabase import create_client, Client
from openai import OpenAI
from config import Settings, get_settings

class APIKeyQueue:
    """Manages API keys with rotation and exhaustion tracking"""
    
    def __init__(self, keys: List[str]):
        if isinstance(keys, str):
            keys = [keys]
        self.keys = deque(keys)
        self.exhausted_keys = set()
        self.daily_limits = {key: 0 for key in keys}
        self.last_reset = datetime.now().date()
        self.total_keys = len(keys)
        
    def get_next_key(self) -> Optional[str]:
        """Get the next available API key"""
        # Reset daily limits if it's a new day
        if datetime.now().date() > self.last_reset:
            self.daily_limits = {key: 0 for key in self.keys}
            self.exhausted_keys.clear()
            self.last_reset = datetime.now().date()
            
        # Find an available key
        for _ in range(len(self.keys)):
            key = self.keys[0]
            self.keys.rotate(-1)  # Move to next key
            
            if key not in self.exhausted_keys and self.daily_limits.get(key, 0) < 100:
                self.daily_limits[key] += 1
                return key
                
        return None
        
    def get_all_keys(self):
        """Get all keys as a list"""
        return list(self.keys)
        
    def add_key(self, key):
        """Add a new key to the queue"""
        if key not in self.keys:
            self.keys.append(key)
            self.daily_limits[key] = 0
            self.total_keys += 1
            
    def remove_key(self, key):
        """Remove a key from the queue"""
        if key in self.keys:
            self.keys.remove(key)
            if key in self.daily_limits:
                del self.daily_limits[key]
            if key in self.exhausted_keys:
                self.exhausted_keys.remove(key)
            self.total_keys -= 1
        
    def mark_exhausted(self, key: str):
        """Mark a key as exhausted"""
        self.exhausted_keys.add(key)
        
    def get_available_count(self) -> int:
        """Get count of available keys"""
        return len([k for k in self.keys if k not in self.exhausted_keys])

class AIICPScorer:
    """Advanced ICP scorer using AI to analyze profile data"""
    
    def __init__(self, openai_api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            
        if not self.api_key:
            raise ValueError("OpenAI API key is required.")
            
        self.llm = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1/",
        )
        self.model = model
        
        self.default_icp_prompt = """You are an ICP (Ideal Customer Profile) evaluator.

Your task is to assess how well this LinkedIn profile matches either of our two ICPs: "operations" or "field_service", using the limited structured fields available.

Profile Data:
{profile_json}

ICP Definitions:

1. Operations ICP:
- Industries: Manufacturing, Industrial Automation, Heavy Equipment, CNC, Robotics, Facility Management, Fleet Ops
- Roles (from 'jobTitle' or 'headline'): Operations Head, Plant Manager, Maintenance Lead, Production Engineer, Digital Transformation Officer
- Seniority: Manager level or above
- Company Maturity Proxy: Company founded before 2020 (≥5 years old)

2. Field Service ICP:
- Industries: Ghost kitchens, cloud kitchens, commercial real estate, managed appliances, kitchen automation, hotels
- Roles: Facility Manager, Maintenance Coordinator, Service Head, Asset Manager
- Seniority: Manager level or above
- Company Maturity Proxy: Founded before 2021 (≥3 years old)

Scoring Criteria (each 0–10):
- industry_fit: Match between 'companyIndustry' and ICP industries
- role_fit: Match between 'jobTitle' or 'headline' and ICP roles
- company_maturity_fit: Based on 'companyFoundedYear' (older = higher score)
- decision_maker: Based on 'seniority', 'functions', or leadership keywords

Scoring Weights:
- industry_fit: 30%
- role_fit: 30%
- company_maturity_fit: 20%
- decision_maker: 20%

Instructions:
- Return best-fit ICP: "operations", "field_service", or "none"
- Use strict logic; if match is weak or unclear, return "none"
- Output ONLY valid JSON (no extra explanation, markdown, or text)

Output Format:
{{
    "industry_fit": <0-10>,
    "role_fit": <0-10>,
    "company_size_fit": <0-10>,
    "decision_maker": <0-10>,
    "total_score": <weighted avg score>,
    "icp_category": "operations" | "field_service" | "none",
    "reasoning": "Brief reasoning based on the fields provided"
}}"""

    def analyze_profile(self, profile: Dict) -> Dict:
        """Analyze a LinkedIn profile using AI to determine ICP fit"""
        try:
            # Prepare profile data for analysis
            profile_for_analysis = {
                "fullName": profile.get("fullName", ""),
                "headline": profile.get("headline", ""),
                "jobTitle": profile.get("jobTitle", ""),
                "companyName": profile.get("companyName", ""),
                "companyIndustry": profile.get("companyIndustry", ""),
                "companySize": profile.get("companySize", ""),
                "location": profile.get("location", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "country": profile.get("country", ""),
                "seniority": profile.get("seniority", ""),
                "departments": profile.get("departments", ""),
                "subdepartments": profile.get("subdepartments", ""),
                "functions": profile.get("functions", ""),
                "companyWebsite": profile.get("companyWebsite", ""),
                "companyDomain": profile.get("companyDomain", ""),
                "companyFoundedYear": profile.get("companyFoundedYear", ""),
                "work_experience_months": profile.get("work_experience_months", ""),
            }
            
            # Remove empty fields to reduce noise
            profile_for_analysis = {k: v for k, v in profile_for_analysis.items() if v}
            
            # Get AI analysis
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": self.default_icp_prompt.format(
                        profile_json=json.dumps(profile_for_analysis, indent=2)
                    )}
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean the response content to ensure it's valid JSON
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse AI response: {str(e)}")
            
            # Validate the analysis
            required_fields = ["industry_fit", "role_fit", "company_size_fit", "decision_maker", 
                             "total_score", "icp_category", "reasoning"]
            
            # Handle potential field mismatch between prompt and code
            if "company_maturity_fit" in analysis and "company_size_fit" not in analysis:
                analysis["company_size_fit"] = analysis["company_maturity_fit"]
                
            for field in required_fields:
                if field not in analysis:
                    raise Exception(f"Missing required field in AI response: {field}")
                
            # Ensure scores are numbers between 0 and 10
            score_fields = ["industry_fit", "role_fit", "company_size_fit", "decision_maker", "total_score"]
            for field in score_fields:
                score = analysis[field]
                if not isinstance(score, (int, float)) or score < 0 or score > 10:
                    raise Exception(f"Invalid score in {field}: {score}")
            
            # Calculate score percentage
            score_percentage = min(100, analysis["total_score"] * 10)
            
            # Determine grade based on score percentage
            if score_percentage >= 80:
                grade = "A+"
            elif score_percentage >= 70:
                grade = "A"
            elif score_percentage >= 60:
                grade = "B+"
            elif score_percentage >= 50:
                grade = "B"
            elif score_percentage >= 40:
                grade = "C+"
            elif score_percentage >= 30:
                grade = "C"
            else:
                grade = "D"
            
            return {
                "total_score": analysis["total_score"],
                "score_percentage": score_percentage,
                "grade": grade,
                "breakdown": {
                    "industry_fit": analysis["industry_fit"],
                    "role_fit": analysis["role_fit"],
                    "company_size_fit": analysis["company_size_fit"],
                    "decision_maker": analysis["decision_maker"],
                    "icp_category": analysis["icp_category"],
                    "reasoning": analysis["reasoning"]
                }
            }
            
        except Exception as e:
            raise Exception(f"Error in AI ICP scoring: {str(e)}")

class LeadService:
    """Service for lead generation and management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Initialize API key queue for Apify
        apify_tokens = self.settings.APIFY_API_TOKEN
        if isinstance(apify_tokens, str):
            if apify_tokens.startswith('['):
                apify_tokens = json.loads(apify_tokens)
            else:
                apify_tokens = [apify_tokens]
        
        self.token_queue = APIKeyQueue(apify_tokens)
        self.ai_icp_scorer = AIICPScorer(self.settings.OPENAI_API_KEY)
        
        # Track used and exhausted keys
        self.used_keys = set()
        self.exhausted_keys = set()
        
        # Track total available keys
        self.total_keys = len(apify_tokens)
        
        # Google API credentials for search method
        self.google_api_key = getattr(self.settings, 'GOOGLE_API_KEY', None)
        self.google_cse_id = getattr(self.settings, 'GOOGLE_CSE_ID', None)
        
        # Status tracking for real-time updates
        self.status_sessions = {}
        self.status_queues = {}
    
    async def generate_leads(self, params: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Generate leads using specified method"""
        try:
            method = params.get("method")
            job_titles = params.get("jobTitles", [])
            locations = params.get("locations", [])
            industries = params.get("industries", [])
            company_sizes = params.get("companySizes", [])
            limit = params.get("limit", 10)
            
            if not method or not job_titles or not locations:
                return {
                    "status": "error",
                    "message": "Missing required parameters"
                }
            
            # Initialize status session if provided
            if session_id:
                self.create_status_session(session_id)
                self.emit_status(session_id, {
                    "type": "started",
                    "message": "Lead generation started",
                    "method": method
                })
            
            leads = []
            
            if method == "apollo":
                leads = await self._search_apollo_leads({
                    "jobTitles": job_titles,
                    "locations": locations,
                    "industries": industries,
                    "companySizes": company_sizes,
                    "limit": limit
                }, session_id)
            elif method == "google_apify":
                leads = await self._search_google_leads({
                    "jobTitles": job_titles,
                    "locations": locations,
                    "industries": industries,
                    "limit": limit
                }, session_id)
            else:
                return {
                    "status": "error",
                    "message": "Invalid method specified"
                }
            
            # Score leads with ICP (only for Apollo method, Google+Apify already includes ICP scoring)
            if self.settings.OPENAI_API_KEY and leads and method == "apollo":
                # Emit status update for ICP scoring start
                if session_id:
                    self.emit_status(session_id, {
                        "type": "icp_scoring_started",
                        "message": f"Scoring {len(leads)} leads with ICP criteria",
                        "total_leads": len(leads),
                        "method": method
                    })
                
                for idx, lead in enumerate(leads):
                    try:
                        icp_analysis = self.ai_icp_scorer.analyze_profile(lead)
                        lead["icp_score"] = icp_analysis["total_score"]  # Use total_score (0-10) for icp_score
                        lead["icp_percentage"] = icp_analysis["score_percentage"]  # Use score_percentage (0-100) for icp_percentage
                        lead["icp_grade"] = icp_analysis["grade"]
                        lead["icp_breakdown"] = icp_analysis["breakdown"]
                        
                        # Emit progress update for each scored lead
                        if session_id:
                            self.emit_status(session_id, {
                                "type": "lead_scored",
                                "message": f"Scored lead {idx + 1} of {len(leads)}",
                                "current_lead": idx + 1,
                                "total_leads": len(leads),
                                "method": method
                            })
                    except Exception as e:
                        print(f"ICP scoring failed for lead: {e}")
                        lead["icp_score"] = 0
                        lead["icp_percentage"] = 0
                        lead["icp_grade"] = "D"
                
                # Emit completion status for ICP scoring
                if session_id:
                    self.emit_status(session_id, {
                        "type": "icp_scoring_completed",
                        "message": f"Completed ICP scoring for {len(leads)} leads",
                        "leads_scored": len(leads),
                        "method": method
                    })
            
            # Save leads to database
            save_result = None
            if leads:
                # Emit status update for database saving start
                if session_id:
                    self.emit_status(session_id, {
                        "type": "saving_leads_started",
                        "message": f"Saving {len(leads)} leads to database",
                        "total_leads": len(leads),
                        "method": method
                    })
                
                save_result = await self._save_leads_to_db(leads)
                
                # Emit completion status for database saving
                if session_id:
                    self.emit_status(session_id, {
                        "type": "saving_leads_completed",
                        "message": f"Successfully saved leads to database",
                        "leads_saved": save_result.get('stats', {}).get('successful', 0) if save_result else 0,
                        "method": method
                    })
            
            # Emit final completion status
            if session_id:
                self.emit_status(session_id, {
                    "type": "generation_completed",
                    "message": f"Lead generation completed successfully! Generated {len(leads)} leads",
                    "total_leads": len(leads),
                    "method": method
                })
            
            return {
                "status": "success",
                "message": f"Generated {len(leads)} leads" + (f". {save_result['message']}" if save_result else ""),
                "leads": leads,
                "count": len(leads),
                "leads_generated": len(leads),
                "save_stats": save_result.get("stats") if save_result else None
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Lead generation failed: {str(e)}"
            }
    
    def get_next_available_key(self):
        """Get next available API key with exhaustion tracking"""
        if not self.token_queue:
            return None
            
        # Try to get a key that hasn't been exhausted
        for _ in range(self.token_queue.total_keys):
            key = self.token_queue.get_next_key()
            if key and key not in self.exhausted_keys:
                return key
        
        # If all keys are exhausted, return None
        return None
    
    def mark_key_exhausted(self, key):
        """Mark an API key as exhausted"""
        if key:
            self.exhausted_keys.add(key)
            if hasattr(self.token_queue, 'mark_exhausted'):
                self.token_queue.mark_exhausted(key)
    
    def check_apollo_exhaustion_response(self, response_data):
        """Check if the response indicates daily run limit exhaustion"""
        if isinstance(response_data, list) and len(response_data) == 1:
            if isinstance(response_data[0], dict):
                message = response_data[0].get("message", "")
                if "exhausted their daily run limit" in message and "2 of 2" in message:
                    return True
        return False
    
    async def _search_apollo_leads(self, params: Dict[str, Any], session_id: str = None) -> List[Dict[str, Any]]:
        """Search leads using Apollo.io via Apify with enhanced API key rotation"""
        try:
            # Emit status update for Apollo search start
            if session_id:
                self.emit_status(session_id, {
                    "type": "apollo_search_started",
                    "message": "Starting Apollo.io search...",
                    "method": "apollo"
                })
            
            # Generate Apollo URL
            apollo_url = self._generate_apollo_url(params)
            max_retries = self.token_queue.total_keys
            num_results = params.get("limit", 50)
            
            for attempt in range(max_retries):
                try:
                    current_api_key = self.get_next_available_key()
                    
                    if current_api_key is None:
                        # No more available keys
                        return []
                    
                    # Call Apify Apollo scraper
                    url = "https://api.apify.com/v2/acts/iJcISG5H8FJUSRoVA/run-sync-get-dataset-items"
                    payload = {
                        "contact_email_exclude_catch_all": True,
                        "contact_email_status_v2": True,
                        "include_email": True,
                        "max_result": num_results,
                        "url": apollo_url
                    }

                    headers = {
                        "Authorization": f"Bearer {current_api_key}",
                        "Content-Type": "application/json"
                    }

                    # Make the request with a longer timeout
                    response = requests.post(url, json=payload, headers=headers, timeout=600)  # 10 minute timeout
                
                    # Handle both 200 and 400 responses since the scraper might return data even with 400
                    if response.status_code not in [200, 201, 400]:
                        if response.status_code == 429:
                            print(f"Rate limit hit with API key. Trying next key...")
                            self.mark_key_exhausted(current_api_key)
                            continue
                        elif response.status_code in [401, 403]:
                            print(f"Authentication failed with API key. Trying next key...")
                            self.mark_key_exhausted(current_api_key)
                            continue
                        else:
                            print(f"Apollo.io API returned unexpected status code {response.status_code}")
                            if attempt == max_retries - 1:
                                return []
                            continue
                    
                    try:
                        results = response.json()

                        # Check for daily limit exhaustion message
                        if self.check_apollo_exhaustion_response(results):
                            print(f"API key {current_api_key[:10]}... has exhausted its daily run limit (2 of 2). Switching to next key...")
                            self.mark_key_exhausted(current_api_key)
                            continue

                        # Check if results is empty or not a list
                        if not results:
                            if attempt == max_retries - 1:
                                print("No results returned from Apollo.io. The search might be too narrow or the credits might be exhausted.")
                                return []
                            continue
                        
                        # If results is a dict with an error message, check for data
                        if isinstance(results, dict):
                            if 'data' in results:
                                results = results['data']
                            elif 'items' in results:
                                results = results['items']
                            else:
                                if attempt == max_retries - 1:
                                    print("Unexpected response format from Apollo.io")
                                    return []
                                continue
                        
                        # Ensure results is a list
                        if not isinstance(results, list):
                            if attempt == max_retries - 1:
                                print("Invalid response format from Apollo.io")
                                return []
                            continue

                        print(f"Found {len(results)} profiles from Apollo.io using API key {current_api_key[:10]}...")
                        
                        # Emit status update for profiles found
                        if session_id:
                            self.emit_status(session_id, {
                                "type": "profiles_found",
                                "message": f"Found {len(results)} profiles from Apollo.io",
                                "profiles_count": len(results),
                                "method": "apollo"
                            })
                        
                        break  # Success, exit the retry loop

                    except json.JSONDecodeError:
                        if attempt == max_retries - 1:
                            print("Invalid JSON response from Apollo.io API")
                            return []
                        continue
                    
                except requests.exceptions.Timeout:
                    print(f"Request timeout with API key. Trying next key...")
                    if attempt == max_retries - 1:
                        print("All API keys failed due to timeout")
                        return []
                    continue
                    
                except requests.exceptions.RequestException as e:
                    print(f"Request failed with API key: {str(e)}")
                    if attempt == max_retries - 1:
                        print(f"All API keys failed: {str(e)}")
                        return []
                    continue
                    
                except Exception as e:
                    print(f"Unexpected error with API key: {str(e)}")
                    if attempt == max_retries - 1:
                        print(f"All API keys failed with unexpected error: {str(e)}")
                        return []
                    continue
            
            # If we get here, we have successful results
            profiles = []
            
            # Emit status update for processing start
            if session_id:
                self.emit_status(session_id, {
                    "type": "processing_started",
                    "message": f"Processing {len(results)} Apollo profiles",
                    "total_profiles": len(results),
                    "method": "apollo"
                })
            
            for idx, result in enumerate(results):
                try:
                    # Get organization data
                    organization = result.get("organization", {}) or {}
                    
                    # Calculate work experience from employment history
                    employment_history = result.get("employment_history", [])
                    total_experience_months = 0
                    for job in employment_history:
                        try:
                            start_date = datetime.strptime(job.get("start_date", ""), "%Y-%m-%d")
                            end_date = datetime.strptime(job.get("end_date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d") if not job.get("current", False) else datetime.now()
                            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                            total_experience_months += max(0, months)
                        except (ValueError, TypeError):
                            continue
                    
                    # Build location string
                    location_parts = []
                    if result.get("city"): location_parts.append(result["city"])
                    if result.get("state"): location_parts.append(result["state"])
                    if result.get("country"): location_parts.append(result["country"])
                    location = ", ".join(location_parts) if location_parts else ""
                    
                    profile = {
                        "linkedin_url": result.get("linkedin_url", ""),
                        "fullName": result.get("name", ""),
                        "firstName": result.get("first_name", ""),
                        "lastName": result.get("last_name", ""),
                        "jobTitle": result.get("title", ""),
                        "email": result.get("email", ""),
                        "email_status": result.get("email_status", ""),
                        "photo_url": result.get("photo_url", ""),
                        "headline": result.get("headline", ""),
                        "location": location,
                        "city": result.get("city", ""),
                        "state": result.get("state", ""),
                        "country": result.get("country", ""),
                        "seniority": result.get("seniority", ""),
                        "departments": result.get("departments", []),
                        "subdepartments": result.get("subdepartments", []),
                        "functions": result.get("functions", []),
                        "work_experience_months": total_experience_months,
                        "employment_history": employment_history,
                        "intent_strength": result.get("intent_strength"),
                        "show_intent": result.get("show_intent", False),
                        "email_domain_catchall": result.get("email_domain_catchall", False),
                        "revealed_for_current_team": result.get("revealed_for_current_team", False),
                        
                        # Company information
                        "companyName": organization.get("name", ""),
                        "companyWebsite": organization.get("website_url", ""),
                        "companyLinkedIn": organization.get("linkedin_url", ""),
                        "companyTwitter": organization.get("twitter_url", ""),
                        "companyFacebook": organization.get("facebook_url", ""),
                        "companyPhone": organization.get("phone", ""),
                        "companyFoundedYear": organization.get("founded_year"),
                        "companySize": organization.get("size", ""),
                        "companyIndustry": organization.get("industry", ""),
                        "companyDomain": organization.get("primary_domain", ""),
                        "companyGrowth6Month": organization.get("organization_headcount_six_month_growth"),
                        "companyGrowth12Month": organization.get("organization_headcount_twelve_month_growth"),
                        "companyGrowth24Month": organization.get("organization_headcount_twenty_four_month_growth"),
                        "send_email_status": "Not Sent",
                    }
                    
                    profiles.append(profile)
                    
                    # Emit progress update for each processed profile
                    if session_id:
                        self.emit_status(session_id, {
                            "type": "profile_processed",
                            "message": f"Processed profile {idx + 1} of {len(results)}",
                            "current_profile": idx + 1,
                            "total_profiles": len(results),
                            "method": "apollo"
                        })
                    
                except Exception as e:
                    print(f"Error processing profile {idx + 1}: {str(e)}")
                    continue

            if profiles:
                print(f"Successfully processed {len(profiles)} Apollo.io profiles")
                
                # Emit completion status
                if session_id:
                    self.emit_status(session_id, {
                        "type": "apollo_search_completed",
                        "message": f"Successfully processed {len(profiles)} Apollo profiles",
                        "profiles_processed": len(profiles),
                        "method": "apollo"
                    })
            else:
                print("No profiles could be processed. Please check your search criteria.")
                
                # Emit error status if no profiles found
                if session_id:
                    self.emit_status(session_id, {
                        "type": "apollo_search_error",
                        "message": "No profiles could be processed from Apollo",
                        "method": "apollo"
                    })
                
            return profiles  # Return all profiles without limiting
            
        except Exception as e:
            print(f"Apollo search error: {e}")
            return []
    
    async def search_linkedin_profiles_google(self, job_titles, locations, industries=None, num_results=50):
        """Search for LinkedIn profiles using Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            print("Google API credentials not configured")
            return []
        
        all_profiles = []
        
        # Create search queries
        search_queries = []
        for job_title in job_titles[:3]:  # Limit to 3 job titles
            for location in locations[:3]:  # Limit to 3 locations
                query = f'site:linkedin.com/in "{job_title}" "{location}"'
                if industries:
                    query += f' "{industries[0]}"'
                search_queries.append(query)
        
        results_per_query = max(1, num_results // len(search_queries))
        
        for query in search_queries:
            try:
                # Call Google Custom Search API
                search_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cse_id,
                    'q': query,
                    'num': min(10, results_per_query)  # Google allows max 10 results per request
                }
                
                response = requests.get(search_url, params=params, timeout=30)
                
                if response.status_code == 403:
                    print("Google API quota exceeded")
                    break
                elif response.status_code != 200:
                    print(f"Google search API error: {response.status_code}")
                    continue
                
                data = response.json()
                items = data.get('items', [])
                
                # Extract LinkedIn URLs
                for item in items:
                    linkedin_url = item.get('link', '')
                    if 'linkedin.com/in/' in linkedin_url:
                        # Clean the URL
                        linkedin_url = linkedin_url.split('?')[0]  # Remove query parameters
                        if linkedin_url not in [p.get('linkedin_url') for p in all_profiles]:
                            profile = {
                                'linkedin_url': linkedin_url,
                                'title': item.get('title', ''),
                                'snippet': item.get('snippet', ''),
                                'source': 'google_search'
                            }
                            all_profiles.append(profile)
                
                # Add a small delay to respect rate limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in Google search: {str(e)}")
                continue
        
        print(f"Found {len(all_profiles)} LinkedIn profiles from Google search")
        return all_profiles[:num_results]
    
    async def _search_google_leads(self, params: Dict[str, Any], session_id: str = None) -> List[Dict[str, Any]]:
        """Search leads using Google Search + Apify enrichment"""
        try:
            # Check if Google API credentials are available
            if not self.google_api_key or not self.google_cse_id:
                print("Google search method requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables")
                return []
            
            # Build search query from parameters
            job_titles = params.get('jobTitles', [])
            locations = params.get('locations', [])
            industries = params.get('industries', [])
            limit = params.get('limit', 50)
            
            if not job_titles or not locations:
                print("Google search requires at least one job title and location")
                return []
            
            # Emit status update for Google search start
            if session_id:
                self.emit_status(session_id, {
                    "type": "google_search_started",
                    "message": "Searching for LinkedIn profiles via Google",
                    "job_titles": job_titles,
                    "locations": locations
                })
            
            # Step 1: Search for LinkedIn profiles using Google
            linkedin_profiles = await self.search_linkedin_profiles_google(
                job_titles, locations, industries, limit
            )
            
            if not linkedin_profiles:
                if session_id:
                    self.emit_status(session_id, {
                        "type": "google_search_completed",
                        "message": "No LinkedIn profiles found via Google search",
                        "profiles_found": 0
                    })
                print("No LinkedIn profiles found via Google search")
                return []
            
            # Emit status update for profiles found
            if session_id:
                self.emit_status(session_id, {
                    "type": "google_search_completed",
                    "message": f"Found {len(linkedin_profiles)} LinkedIn profiles",
                    "profiles_found": len(linkedin_profiles)
                })
            
            # Step 2: Enrich profiles using Apify
            enriched_profiles = await self.batch_enrich_profiles([p['linkedin_url'] for p in linkedin_profiles], session_id)
            
            return enriched_profiles
            
        except Exception as e:
            if session_id:
                self.emit_status(session_id, {
                    "type": "error",
                    "message": f"Google search error: {str(e)}"
                })
            print(f"Google search error: {e}")
            return []
    
    async def batch_enrich_profiles(self, linkedin_urls, session_id: str = None):
        """Enrich multiple LinkedIn profiles using Apify"""
        enriched_profiles = []
        total_profiles = len(linkedin_urls)
        
        # Emit status update for enrichment start
        if session_id:
            self.emit_status(session_id, {
                "type": "apify_enrichment_started",
                "message": f"Starting Apify enrichment for {total_profiles} profiles",
                "total_profiles": total_profiles,
                "completed": 0
            })
        
        for i, linkedin_url in enumerate(linkedin_urls, 1):
            try:
                # Emit progress update
                if session_id:
                    self.emit_status(session_id, {
                        "type": "apify_enrichment_progress",
                        "message": f"Enriching profile {i} of {total_profiles}",
                        "current_profile": i,
                        "total_profiles": total_profiles,
                        "linkedin_url": linkedin_url
                    })
                
                enriched_profile = await self.enrich_profile_with_apify(linkedin_url)
                if enriched_profile:
                    enriched_profiles.append(enriched_profile)
                    
                    # Emit success update for individual profile
                    if session_id:
                        self.emit_status(session_id, {
                            "type": "profile_enriched",
                            "message": f"Successfully enriched profile {i}",
                            "profile_name": enriched_profile.get('fullName', 'Unknown'),
                            "completed": len(enriched_profiles)
                        })
                        
            except Exception as e:
                if session_id:
                    self.emit_status(session_id, {
                        "type": "profile_enrichment_error",
                        "message": f"Error enriching profile {i}: {str(e)}",
                        "linkedin_url": linkedin_url
                    })
                print(f"Error enriching profile {linkedin_url}: {str(e)}")
                continue
        
        # Emit completion status
        if session_id:
            self.emit_status(session_id, {
                "type": "apify_enrichment_completed",
                "message": f"Completed enrichment: {len(enriched_profiles)} profiles successfully enriched",
                "total_enriched": len(enriched_profiles),
                "total_attempted": total_profiles
            })
        
        return enriched_profiles
    
    def parse_location(self, location_str):
        """Parse location string to extract city, state, and country"""
        if not location_str:
            return {"city": None, "state": None, "country": None}
        
        # Split by comma and clean up
        parts = [part.strip() for part in location_str.split(',')]
        
        city = None
        state = None
        country = None
        
        if len(parts) == 1:
            # Could be city, state, or country
            city = parts[0]
        elif len(parts) == 2:
            # Could be "City, State" or "City, Country"
            city = parts[0]
            # Check if second part looks like a US state (2-3 characters)
            if len(parts[1]) <= 3:
                state = parts[1]
            else:
                country = parts[1]
        elif len(parts) >= 3:
            # "City, State, Country" format
            city = parts[0]
            state = parts[1]
            country = parts[2]
        
        return {
            "city": city,
            "state": state,
            "country": country
        }
    
    async def enrich_profile_with_apify(self, linkedin_urls):
        """Enrich LinkedIn profiles using Apify in batch"""
        if isinstance(linkedin_urls, str):
            linkedin_urls = [linkedin_urls]  # Convert single URL to list for backward compatibility
            
        print(f"Starting Apify enrichment for {len(linkedin_urls)} profiles")
        max_retries = self.total_keys
        
        for attempt in range(max_retries):
            try:
                current_api_key = self.get_next_available_key()
                
                if current_api_key is None:
                    print("No more available Apify API keys")
                    return []
                
                # Call Apify LinkedIn scraper (no cookies required)
                url = (
                "https://api.apify.com/v2/acts/dev_fusion~linkedin-profile-scraper/"
                "run-sync-get-dataset-items"
            )
                payload = {
                    "profileUrls": linkedin_urls
                }
                
                headers = {
                    "Authorization": f"Bearer {current_api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=300)
                
                if response.status_code not in [200, 201]:
                    if response.status_code == 429:
                        print(f"Rate limit hit with API key. Trying next key...")
                        self.mark_key_exhausted(current_api_key)
                        continue
                    elif response.status_code in [401, 403]:
                        print(f"Authentication failed with API key. Trying next key...")
                        self.mark_key_exhausted(current_api_key)
                        continue
                    else:
                        print(f"Apify API returned status code {response.status_code}")
                        if attempt == max_retries - 1:
                            return []
                        continue
                
                try:
                    results = response.json()
                    
                    if not results or not isinstance(results, list) or len(results) == 0:
                        if attempt == max_retries - 1:
                            print(f"No data returned for batch request")
                            return []
                        continue
                    
                    # Process all profiles in the batch
                    enriched_profiles = []
                    
                    for profile_data in results:
                        # Parse location into city, state, and country
                        location = profile_data.get("addressWithCountry", "")
                        location_parts = self.parse_location(location)
                        
                        # Process the enriched profile data with comprehensive mapping
                        # Map all fields returned by Apify scraper to database schema
                        enriched_profile = {
                            "linkedin_url": profile_data.get("linkedinUrl", ""),
                            "firstName": profile_data.get("firstName", ""),
                            "lastName": profile_data.get("lastName", ""),
                            "fullName": profile_data.get("fullName", ""),
                            "headline": profile_data.get("headline", ""),
                            "email": profile_data.get("email"),
                            "jobTitle": profile_data.get("jobTitle", ""),
                            "companyName": profile_data.get("companyName", ""),
                            "companyIndustry": profile_data.get("companyIndustry", ""),
                            "companyWebsite": profile_data.get("companyWebsite", ""),
                            "companyLinkedin": profile_data.get("companyLinkedin", ""),
                            "companySize": profile_data.get("companySize", ""),
                            "location": location,
                            "city": location_parts["city"],
                            "state": location_parts["state"],
                            "country": location_parts["country"],
                            "about": profile_data.get("about", ""),
                            "experience": json.dumps(profile_data.get("experiences", [])),
                            "connections": profile_data.get("connections", 0),
                            "followers": profile_data.get("followers", 0),
                            "photo_url": profile_data.get("profilePic"),
                            "scraped_at": datetime.now().isoformat(),
                            "scraping_status": "success"
                        }
                        
                        # Perform ICP scoring for each profile
                        try:
                            icp_analysis = self.ai_icp_scorer.analyze_profile(enriched_profile)
                            # Map ICP analysis results to expected field names
                            enriched_profile["icp_score"] = icp_analysis["total_score"]
                            enriched_profile["icp_percentage"] = icp_analysis["score_percentage"]
                            enriched_profile["icp_grade"] = icp_analysis["grade"]
                            enriched_profile["icp_breakdown"] = icp_analysis["breakdown"]
                        except Exception as e:
                            print(f"ICP scoring failed for {enriched_profile.get('linkedin_url', 'unknown')}: {str(e)}")
                            # Set default ICP values if scoring fails
                            enriched_profile["icp_score"] = 0
                            enriched_profile["icp_percentage"] = 0
                            enriched_profile["icp_grade"] = "D"
                            enriched_profile["icp_breakdown"] = {"reasoning": "ICP scoring failed"}
                        
                        enriched_profiles.append(enriched_profile)
                    
                    return enriched_profiles
                    
                except json.JSONDecodeError:
                    if attempt == max_retries - 1:
                        print(f"Invalid JSON response for batch request")
                        return []
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"Request timeout for batch request. Trying next key...")
                if attempt == max_retries - 1:
                    print(f"All API keys failed due to timeout for batch request")
                    return []
                continue
                
            except requests.exceptions.RequestException as e:
                print(f"Request failed for batch request: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"All API keys failed for batch request: {str(e)}")
                    return []
                continue
                
            except Exception as e:
                print(f"Unexpected error for batch request: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"All API keys failed with unexpected error for batch request: {str(e)}")
                    return []
                continue
        
        return []
    
    def _generate_apollo_url(self, query_data: dict) -> str:
        """Generate Apollo.io search URL from query parameters"""
        print(f"DEBUG: Apollo URL generation with query_data: {query_data}")
        
        # Base URL for Apollo
        base_url = 'https://app.apollo.io/#/people'

        # List to hold each part of the query string
        query_parts = []

        # Add static parameters
        query_parts.append('sortByField=recommendations_score')
        query_parts.append('sortAscending=false')
        query_parts.append('page=1')

        # Helper function to process and add array parameters to query_parts
        def add_array_params(param_name: str, values: List[str]):
            for val in values:
                # Replace '+' with space then encode the value
                decoded_value = val.replace('+', ' ')
                query_parts.append(f"{param_name}[]={requests.utils.quote(decoded_value)}")

        # Process job titles (maps to personTitles[])
        # Support both 'jobTitles' (new format) and 'job_title' (legacy format)
        job_titles = query_data.get('jobTitles') or query_data.get('job_title', [])
        if job_titles and isinstance(job_titles, list):
            add_array_params('personTitles', job_titles)

        # Process locations (maps to personLocations[])
        # Support both 'locations' (new format) and 'location' (legacy format)
        locations = query_data.get('locations') or query_data.get('location', [])
        if locations and isinstance(locations, list):
            add_array_params('personLocations', locations)

        # Process industries (maps to qOrganizationKeywordTags[])
        # Support both 'industries' (new format) and 'business' (legacy format)
        industries = query_data.get('industries') or query_data.get('business', [])
        if industries and isinstance(industries, list):
            add_array_params('qOrganizationKeywordTags', industries)
            
        # Process company sizes (maps to organizationNumEmployeesRanges[])
        # Support both 'companySizes' (new format) and 'employee_ranges' (legacy format)
        company_sizes = query_data.get('companySizes') or query_data.get('employee_ranges', [])
        if company_sizes and isinstance(company_sizes, list):
            add_array_params('organizationNumEmployeesRanges', company_sizes)

        # Add static included organization keyword fields
        query_parts.append('includedOrganizationKeywordFields[]=tags')
        query_parts.append('includedOrganizationKeywordFields[]=name')

        # Only add default employee ranges if not already provided
        if not company_sizes:
            employee_ranges = [
                "1,10",
                "11,20",
                "21,50",
                "51,100",
                "101,200"
            ]
            add_array_params('organizationNumEmployeesRanges', employee_ranges)

        # Combine all query parts with '&' to form the full query string
        query_string = '&'.join(query_parts)

        # Build the final URL
        final_url = f"{base_url}?{query_string}"
        
        print(f"DEBUG: Generated Apollo URL: {final_url}")
        print(f"DEBUG: Processed - Job Titles: {job_titles}, Locations: {locations}, Industries: {industries}, Company Sizes: {company_sizes}")

        return final_url
    
    def _clean_apollo_profile(self, profile: Dict) -> Dict:
        """Clean and format Apollo profile data"""
        try:
            # Extract and clean the profile data
            cleaned = {
                'fullName': profile.get('name', ''),
                'firstName': profile.get('first_name', ''),
                'lastName': profile.get('last_name', ''),
                'headline': profile.get('headline', ''),
                'jobTitle': profile.get('title', ''),
                'email': profile.get('email', ''),
                'linkedin_url': profile.get('linkedin_url', ''),
                'companyName': profile.get('organization_name', ''),
                'companyIndustry': profile.get('organization_industry', ''),
                'companySize': profile.get('organization_num_employees', ''),
                'companyWebsite': profile.get('organization_website_url', ''),
                'location': profile.get('city', ''),
                'city': profile.get('city', ''),
                'state': profile.get('state', ''),
                'country': profile.get('country', ''),
                'seniority': profile.get('seniority', ''),
                'departments': profile.get('departments', ''),
                'functions': profile.get('functions', ''),
                'phone': profile.get('phone', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Remove empty values
            cleaned = {k: v for k, v in cleaned.items() if v}
            
            return cleaned
            
        except Exception as e:
            print(f"Error cleaning Apollo profile: {str(e)}")
            return None
    
    def map_profile_fields_to_db(self, profile: Dict) -> Dict:
        """Map camelCase profile fields to snake_case database column names."""
        # Field mapping from camelCase (Apollo/Apify) to snake_case (database)
        field_mapping = {
            'fullName': 'full_name',
            'firstName': 'first_name', 
            'lastName': 'last_name',
            'jobTitle': 'job_title',
            'companyName': 'company_name',
            'companyDomain': 'company_domain',
            'companyIndustry': 'company_industry',
            'companySize': 'company_size',
            'companyWebsite': 'company_website',
            'companyLinkedIn': 'company_linkedin',
            'companyLinkedin': 'company_linkedin',  # Handle both variations
            'companyTwitter': 'company_twitter',
            'companyFacebook': 'company_facebook',
            'companyPhone': 'company_phone',
            'companyFoundedYear': 'company_founded_year',
            'companyFoundedIn': 'company_founded_year',  # Handle LinkedIn variation
            'companyGrowth6Month': 'company_growth_6month',
            'companyGrowth12Month': 'company_growth_12month',
            'companyGrowth24Month': 'company_growth_24month',
            'linkedinUrl': 'linkedin_url',
            'linkedin_url': 'linkedin_url',
            'emailAddress': 'email_address',
            'phoneNumber': 'phone_number',
            'mobileNumber': 'phone_number',  # Handle LinkedIn variation
            'photo_url': 'photo_url',
            'profilePic': 'photo_url',  # Handle LinkedIn variation
            'profilePicHighQuality': 'photo_url',  # Use high quality if available
            'work_experience_months': 'work_experience_months',
            'employment_history': 'employment_history',
            'intent_strength': 'intent_strength',
            'show_intent': 'show_intent',
            'email_domain_catchall': 'email_domain_catchall',
            'revealed_for_current_team': 'revealed_for_current_team',
            'icpScore': 'icp_score',
            'icpGrade': 'icp_grade', 
            'icpPercentage': 'icp_percentage',
            'icpBreakdown': 'icp_breakdown',
            'icp_score': 'icp_score',
            'icp_grade': 'icp_grade',
            'icp_percentage': 'icp_percentage',
            'icp_breakdown': 'icp_breakdown',
            'total_score': 'icp_score',
            'score_percentage': 'icp_percentage',
            'grade': 'icp_grade',
            'breakdown': 'icp_breakdown',
            'createdAt': 'created_at',
            # LinkedIn enrichment specific fields
            'about': 'about',
            'headline': 'headline',
            'experiences': 'experience',  # Map experiences array to experience JSON field
            # Remove non-existent database columns to prevent schema errors
            # 'connections': 'connections',  # Not in DB schema - removed
            # 'followers': 'followers',  # Not in DB schema - removed
            # 'currentJobDuration': 'current_job_duration',  # Not in DB schema - removed
            # 'currentJobDurationInYrs': 'current_job_duration_years',  # Not in DB schema - removed
            # 'topSkillsByEndorsements': 'top_skills',  # Not in DB schema - removed
            'addressCountryOnly': 'country',
            'addressWithCountry': 'location',
            'addressWithoutCountry': 'location',
            # 'publicIdentifier': 'public_identifier',  # Not in DB schema - removed
            # 'openConnection': 'open_connection',  # Not in DB schema - removed
            # 'urn': 'linkedin_urn'  # Not in DB schema - removed
        }
        
        # Define integer fields that should be None instead of empty string when null
        integer_fields = {
            'work_experience_months', 'company_founded_year', 'icp_score', 'icp_percentage'
        }
        
        mapped_profile = {}
        for key, value in profile.items():
            # Use mapped field name if available, otherwise use original key in snake_case
            db_field = field_mapping.get(key, key)
            
            # Special handling for specific fields
            if key == 'profilePicHighQuality' and value and 'profilePic' in profile:
                # Prefer high quality profile pic over regular one
                db_field = 'photo_url'
            elif key == 'profilePic' and 'profilePicHighQuality' in profile and profile['profilePicHighQuality']:
                # Skip regular profile pic if high quality is available
                continue
            
            # Convert lists and dicts to JSON strings
            if isinstance(value, (list, dict)):
                mapped_profile[db_field] = json.dumps(value)
            # Handle None values based on field type
            elif value is None or value == "":
                if db_field in integer_fields:
                    mapped_profile[db_field] = None  # Keep as None for integer fields
                else:
                    mapped_profile[db_field] = ""  # Convert to empty string for text fields
            # Handle string values that might contain backticks (clean them)
            elif isinstance(value, str):
                # For integer fields, try to convert string to int, otherwise set to None
                if db_field in integer_fields:
                    try:
                        mapped_profile[db_field] = int(value) if value.strip() else None
                    except (ValueError, AttributeError):
                        mapped_profile[db_field] = None
                else:
                    mapped_profile[db_field] = value.replace('`', '')
            else:
                mapped_profile[db_field] = value
                
        return mapped_profile

    def get_valid_db_columns(self):
        """Get list of valid columns from the leads table schema."""
        # Define the current leads table schema columns based on the complete migration
        # This matches the 20241201_create_complete_leads_table.sql schema
        base_columns = {
            'id', 'linkedin_url', 'full_name', 'first_name', 'last_name', 'headline', 'about',
            'email', 'email_address', 'email_status', 'phone_number', 'job_title', 'seniority',
            'departments', 'subdepartments', 'functions', 'work_experience_months', 'employment_history',
            'location', 'city', 'state', 'country', 'company_name', 'company_website', 'company_domain',
            'company_linkedin', 'company_twitter', 'company_facebook', 'company_phone', 'company_size',
            'company_industry', 'company_founded_year', 'company_growth_6month', 'company_growth_12month',
            'company_growth_24month', 'photo_url', 'experience', 'intent_strength', 'show_intent',
            'email_domain_catchall', 'revealed_for_current_team', 'icp_score', 'icp_percentage',
            'icp_grade', 'icp_breakdown', 'send_email_status', 'scraping_status', 'error_message',
            'scraped_at', 'created_at', 'updated_at'
        }
        
        # Additional columns that might be added in future or custom implementations
        # These will be filtered out gracefully if they don't exist
        # Removed non-existent columns to prevent schema errors
        extended_columns = set()  # Empty set - all required columns are in base_columns
        
        return base_columns.union(extended_columns)

    async def _save_leads_to_db(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save leads to Supabase database with graceful handling of missing columns."""
        if not leads:
            return {"status": "warning", "message": "No leads to save to Supabase."}
            
        try:
            # Get valid database columns
            valid_columns = self.get_valid_db_columns()
            
            # Track stats for summary
            total_leads = len(leads)
            successful_inserts = 0
            duplicate_leads = 0
            failed_inserts = 0
            skipped_fields = set()
            
            for lead in leads:
                try:
                    # Map profile fields to database column names
                    clean_profile = self.map_profile_fields_to_db(lead)
                    
                    # Filter out fields that don't exist in the database schema
                    filtered_profile = {}
                    for key, value in clean_profile.items():
                        if key in valid_columns:
                            filtered_profile[key] = value
                        else:
                            skipped_fields.add(key)
                    
                    # Add required fields if not present
                    if "id" not in filtered_profile:
                        filtered_profile["id"] = str(uuid.uuid4())
                    if "created_at" not in filtered_profile:
                        filtered_profile["created_at"] = datetime.now().isoformat()
                    if "updated_at" not in filtered_profile:
                        filtered_profile["updated_at"] = datetime.now().isoformat()
                        
                    # Insert data into Supabase
                    result = self.supabase.table("leads").insert(filtered_profile).execute()
                    
                    # Check if insert was successful
                    if result.data:
                        successful_inserts += 1
                    else:
                        failed_inserts += 1
                        
                except Exception as profile_e:
                    # Check if it's a duplicate key violation
                    if "duplicate key" in str(profile_e).lower() or "unique constraint" in str(profile_e).lower():
                        duplicate_leads += 1
                    else:
                        failed_inserts += 1
                        print(f"Error inserting profile: {str(profile_e)}")
            
            # Generate summary message
            message = f"Saved {successful_inserts} new leads to Supabase"
            if duplicate_leads > 0:
                message += f", {duplicate_leads} duplicates skipped"
            if failed_inserts > 0:
                message += f", {failed_inserts} failed"
            if skipped_fields:
                print(f"Note: Skipped fields not in database schema: {', '.join(sorted(skipped_fields))}")
                
            return {
                "status": "success" if successful_inserts > 0 else "warning",
                "message": message,
                "stats": {
                    "total": total_leads,
                    "successful": successful_inserts,
                    "duplicates": duplicate_leads,
                    "failed": failed_inserts,
                    "skipped_fields": list(skipped_fields)
                }
            }
                
        except Exception as e:
            return {"status": "warning", "message": f"Error saving to Supabase: {str(e)}"}
    
    async def get_leads(
        self,
        page: int = 1,
        limit: int = 50,
        search: str = "",
        min_score: float = 0,
        max_score: float = 100,
        company: str = "",
        job_title: str = "",
        email_status: str = "",
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get leads with filtering and pagination"""
        try:
            # Build query
            query = self.supabase.table("leads").select("*", count="exact")
            
            # Apply filters
            if search:
                query = query.or_(f"full_name.ilike.%{search}%,company_name.ilike.%{search}%,job_title.ilike.%{search}%,email.ilike.%{search}%")
            
            if min_score > 0 or max_score < 100:
                query = query.gte("icp_score", min_score).lte("icp_score", max_score)
            
            if company:
                query = query.ilike("company_name", f"%{company}%")
            
            if job_title:
                query = query.ilike("job_title", f"%{job_title}%")
            
            if email_status:
                query = query.eq("email_status", email_status)
            
            # Apply sorting
            if sort_order == "asc":
                query = query.order(sort_by)
            else:
                query = query.order(sort_by, desc=True)
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            
            total_count = result.count if hasattr(result, 'count') else 0
            total_pages = (total_count + limit - 1) // limit
            
            return {
                "status": "success",
                "data": result.data or [],
                "leads": result.data or [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "totalPages": total_pages,
                    "hasNext": page < total_pages,
                    "hasPrev": page > 1
                },
                "total": total_count
            }
            
        except Exception as e:
            raise Exception(f"Error fetching leads: {str(e)}")
    
    async def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a lead"""
        try:
            # Add updated timestamp
            lead_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("leads").update(lead_data).eq("id", lead_id).execute()
            
            return {
                "status": "success",
                "message": "Lead updated successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error updating lead: {str(e)}")
    
    async def delete_lead(self, lead_id: str) -> Dict[str, Any]:
        """Delete a lead"""
        try:
            result = self.supabase.table("leads").delete().eq("id", lead_id).execute()
            
            return {
                "status": "success",
                "message": "Lead deleted successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error deleting lead: {str(e)}")
    
    async def bulk_delete_leads(self, lead_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple leads"""
        try:
            result = self.supabase.table("leads").delete().in_("id", lead_ids).execute()
            
            return {
                "status": "success",
                "message": f"Deleted {len(lead_ids)} leads successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error deleting leads: {str(e)}")
    
    async def get_metrics(self, time_range: str = "30d") -> Dict[str, Any]:
        """Get lead metrics"""
        try:
            # Calculate date range
            now = datetime.now()
            if time_range == "7d":
                start_date = now - timedelta(days=7)
            elif time_range == "30d":
                start_date = now - timedelta(days=30)
            elif time_range == "90d":
                start_date = now - timedelta(days=90)
            else:
                start_date = now - timedelta(days=30)
            
            # Fetch all leads
            all_leads_result = self.supabase.table("leads").select("*").execute()
            all_leads = all_leads_result.data or []
            
            # Fetch recent leads
            recent_leads_result = self.supabase.table("leads").select("*").gte("created_at", start_date.isoformat()).execute()
            recent_leads = recent_leads_result.data or []
            
            # Calculate metrics
            total_leads = len(all_leads)
            new_leads = len(recent_leads)
            
            # Calculate average score
            scores = [lead.get("icp_score", 0) for lead in all_leads if lead.get("icp_score") is not None]
            average_score = sum(scores) / len(scores) if scores else 0
            
            # Calculate grade distribution
            grades = [lead.get("icp_grade", "D") for lead in all_leads]
            grade_counts = {}
            for grade in grades:
                grade_counts[grade] = grade_counts.get(grade, 0) + 1
            
            top_grade = max(grade_counts.items(), key=lambda x: x[1])[0] if grade_counts else "D"
            
            # Email metrics (simplified)
            emails_sent = len([lead for lead in all_leads if lead.get("email_status") == "sent"])
            emails_opened = len([lead for lead in all_leads if lead.get("email_status") == "opened"])
            emails_clicked = len([lead for lead in all_leads if lead.get("email_status") == "clicked"])
            emails_replied = len([lead for lead in all_leads if lead.get("email_status") == "replied"])
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "totalLeads": total_leads,
                        "newLeads": new_leads,
                        "averageScore": round(average_score, 2),
                        "topGrade": top_grade,
                        "emailsSent": emails_sent,
                        "emailsOpened": emails_opened,
                        "emailsClicked": emails_clicked,
                        "emailsReplied": emails_replied
                    },
                    "breakdown": {
                        "grades": grade_counts
                    },
                    "trends": {
                        "timeRange": time_range
                    }
                }
            }
            
        except Exception as e:
            raise Exception(f"Error fetching metrics: {str(e)}")
    
    def create_status_session(self, session_id: str):
        """Create a new status tracking session"""
        self.status_sessions[session_id] = {
            "created_at": datetime.now(),
            "active": True
        }
        self.status_queues[session_id] = asyncio.Queue()
    
    def emit_status(self, session_id: str, status: Dict[str, Any]):
        """Emit a status update for a session"""
        if session_id in self.status_queues:
            try:
                self.status_queues[session_id].put_nowait({
                    "timestamp": datetime.now().isoformat(),
                    **status
                })
            except asyncio.QueueFull:
                pass  # Skip if queue is full
    
    async def get_status_updates(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Get status updates for a session via async generator"""
        if session_id not in self.status_queues:
            self.create_status_session(session_id)
        
        queue = self.status_queues[session_id]
        
        try:
            while self.status_sessions.get(session_id, {}).get("active", False):
                try:
                    # Wait for status update with timeout
                    status = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield status
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
        finally:
            # Clean up session
            if session_id in self.status_sessions:
                del self.status_sessions[session_id]
            if session_id in self.status_queues:
                del self.status_queues[session_id]
    
    def close_status_session(self, session_id: str):
        """Close a status tracking session"""
        if session_id in self.status_sessions:
            self.status_sessions[session_id]["active"] = False