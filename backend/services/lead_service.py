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
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
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
    """AI-powered ICP (Ideal Customer Profile) scorer"""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Initialize OpenAI client
        if self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
            print(f"[AI ICP] OpenAI client initialized successfully")
        else:
            self.openai_client = None
            print(f"[AI ICP] OpenAI API key not configured - using default scores")
    
    def clean_ai_json_response(self, response_text: str) -> str:
        """Clean AI response to extract valid JSON"""
        if not response_text:
            return "{}"
        
        # Remove leading/trailing whitespace and newlines
        cleaned = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        # Remove extra quotes if the entire response is wrapped in quotes
        if cleaned.startswith('"') and cleaned.endswith('"') and cleaned.count('"') == 2:
            cleaned = cleaned[1:-1]
        
        # Handle cases where response starts with newline followed by quote
        if cleaned.startswith('\n"') and cleaned.endswith('"'):
            cleaned = cleaned[2:-1]
        
        return cleaned.strip()
    
    async def analyze_profile(self, profile_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze a profile using AI and return ICP scores"""
        try:
            if not self.openai_client:
                # Return default scores if OpenAI is not configured
                return {
                    "icp_score": 50.0,
                    "icp_percentage": 50.0,
                    "icp_grade": "C",
                    "icp_breakdown": {
                        "industry_fit": 5.0,
                        "role_fit": 5.0,
                        "company_size_fit": 5.0,
                        "decision_maker": 5.0,
                        "reasoning": "OpenAI not configured"
                    }
                }
            
            # Get default config if none provided
            if not config:
                config = await self._get_default_config()
            
            # Prepare profile data for analysis - use all available fields from Apollo data (matching main.py)
            profile_summary = {
                "fullName": profile_data.get("fullName", ""),
                "headline": profile_data.get("headline", ""),
                "jobTitle": profile_data.get("jobTitle", ""),
                "companyName": profile_data.get("companyName", ""),
                "companyIndustry": profile_data.get("companyIndustry", ""),
                "companySize": profile_data.get("companySize", ""),
                "location": profile_data.get("location", ""),
                "city": profile_data.get("city", ""),
                "state": profile_data.get("state", ""),
                "country": profile_data.get("country", ""),
                "seniority": profile_data.get("seniority", ""),
                "departments": profile_data.get("departments", ""),
                "subdepartments": profile_data.get("subdepartments", ""),
                "functions": profile_data.get("functions", ""),
                "companyWebsite": profile_data.get("companyWebsite", ""),
                "companyDomain": profile_data.get("companyDomain", ""),
                "companyFoundedYear": profile_data.get("companyFoundedYear", ""),
                "work_experience_months": profile_data.get("work_experience_months", ""),
            }
            
            # Remove empty fields to reduce noise (matching main.py)
            profile_summary = {k: v for k, v in profile_summary.items() if v}
            
            # Get ICP criteria from config
            target_industries = config.get("target_industries", [])
            target_roles = config.get("target_roles", [])
            target_company_sizes = config.get("company_size_ranges", [])
            custom_prompt = config.get("custom_prompt", "")
            
            # Use the default prompt from main.py
            prompt_template = self._get_default_prompt()
            # Safely replace the profile_json placeholder to avoid format string errors
            profile_json_str = json.dumps(profile_summary, indent=2)
            prompt = prompt_template.replace("{profile_json}", profile_json_str)
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing LinkedIn profiles for sales qualification. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract and clean the response
            ai_response = response.choices[0].message.content
            cleaned_response = self.clean_ai_json_response(ai_response)
            
            # Parse JSON response
            try:
                scores = json.loads(cleaned_response)
                
                # Validate the analysis - match main.py structure
                required_fields = ["industry_fit", "role_fit", "company_size_fit", "decision_maker", 
                                 "total_score", "icp_category", "reasoning"]
                
                # Handle potential field mismatch between prompt and code
                if "company_maturity_fit" in scores and "company_size_fit" not in scores:
                    scores["company_size_fit"] = scores["company_maturity_fit"]
                    
                for field in required_fields:
                    if field not in scores:
                        if field in ["industry_fit", "role_fit", "company_size_fit", "decision_maker"]:
                            scores[field] = 5.0  # Default score
                        elif field == "total_score":
                            scores[field] = 5.0
                        elif field == "icp_category":
                            scores[field] = "none"
                        elif field == "reasoning":
                            scores[field] = "Default reasoning"
                            
                # Ensure scores are numbers between 0 and 10
                score_fields = ["industry_fit", "role_fit", "company_size_fit", "decision_maker", "total_score"]
                for field in score_fields:
                    if field in scores:
                        score = scores[field]
                        if not isinstance(score, (int, float)) or score < 0 or score > 10:
                            scores[field] = 5.0  # Default to middle score
                        scores[field] = max(0, min(10, float(scores[field])))
                
                # Use the total_score from AI response (matching main.py logic)
                total_score = scores.get("total_score", 5.0)
                
                # Calculate score percentage (matching main.py: total_score * 10)
                score_percentage = min(100, total_score * 10)
                
                # Determine grade based on score percentage (matching main.py)
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
                
                # Use reasoning from AI response
                reasoning = scores.get("reasoning", "AI analysis completed")
                
                return {
                    "icp_score": round(total_score, 2),
                    "icp_percentage": round(score_percentage, 2),
                    "icp_grade": grade,
                    "icp_breakdown": {
                        "industry_fit": scores["industry_fit"],
                        "role_fit": scores["role_fit"],
                        "company_size_fit": scores["company_size_fit"],
                        "decision_maker": scores["decision_maker"],
                        "reasoning": reasoning
                    }
                }
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error in AI ICP scoring: {e}")
                print(f"Cleaned response: {cleaned_response}")
                # Return default scores on JSON error
                return {
                    "icp_score": 50.0,
                    "icp_percentage": 50.0,
                    "icp_grade": "C",
                    "icp_breakdown": {
                        "industry_fit": 5.0,
                        "role_fit": 5.0,
                        "company_size_fit": 5.0,
                        "decision_maker": 5.0,
                        "reasoning": "JSON parsing error"
                    }
                }
                
        except Exception as e:
            print(f"Error in AI ICP scoring: {e}")
            # Return default scores on any error
            error_msg = str(e).replace('{', '{{').replace('}', '}}')
            return {
                "icp_score": 50.0,
                "icp_percentage": 50.0,
                "icp_grade": "C",
                "icp_breakdown": {
                    "industry_fit": 5.0,
                    "role_fit": 5.0,
                    "company_size_fit": 5.0,
                    "decision_maker": 5.0,
                    "reasoning": f"Error: {error_msg}"
                }
            }
    
    def _calculate_grade(self, score_percentage: float) -> str:
        """Calculate letter grade from score percentage"""
        if score_percentage >= 90:
            return "A+"
        elif score_percentage >= 80:
            return "A"
        elif score_percentage >= 70:
            return "B+"
        elif score_percentage >= 60:
            return "B"
        elif score_percentage >= 50:
            return "C+"
        elif score_percentage >= 40:
            return "C"
        elif score_percentage >= 30:
            return "D+"
        else:
            return "D"
    
    def _generate_reasoning(self, profile_summary: Dict[str, Any], scores: Dict[str, float]) -> str:
        """Generate human-readable reasoning for the score"""
        reasoning_parts = []
        
        # Industry reasoning
        if scores["industry_fit"] >= 8:
            reasoning_parts.append(f"Strong industry match with {profile_summary['industry']}")
        elif scores["industry_fit"] >= 5:
            reasoning_parts.append(f"Partial industry alignment with {profile_summary['industry']}")
        else:
            reasoning_parts.append("Limited industry fit")
        
        # Role reasoning
        if scores["role_fit"] >= 8:
            reasoning_parts.append(f"Excellent role match: {profile_summary['job_title']}")
        elif scores["role_fit"] >= 5:
            reasoning_parts.append(f"Good role alignment: {profile_summary['job_title']}")
        else:
            reasoning_parts.append("Role doesn't strongly align with targets")
        
        # Company size reasoning
        if scores["company_size_fit"] >= 8:
            reasoning_parts.append(f"Company size ({profile_summary['company_size']}) fits target criteria")
        elif scores["company_size_fit"] >= 5:
            reasoning_parts.append(f"Company size ({profile_summary['company_size']}) partially matches")
        else:
            reasoning_parts.append("Company size outside preferred range")
        
        # Decision maker reasoning
        if scores["decision_maker"] >= 8:
            reasoning_parts.append("Strong decision-making authority indicated")
        elif scores["decision_maker"] >= 5:
            reasoning_parts.append("Some decision-making influence")
        else:
            reasoning_parts.append("Limited decision-making authority")
        
        return ". ".join(reasoning_parts) + "."
    
    def _get_default_prompt(self) -> str:
        """Get the default ICP prompt"""
        return """You are an ICP (Ideal Customer Profile) evaluator.

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

    def get_prompt(self) -> Dict[str, Any]:
        """Get the current ICP prompt configuration"""
        try:
            # Try to get custom prompt from database
            result = self.supabase.table("icp_prompt_config").select("*").limit(1).execute()
            if result.data:
                config = result.data[0]
                return {
                    "status": "success",
                    "data": {
                        "prompt": config.get("prompt", self._get_default_prompt()),
                        "default_values": {
                            "target_roles": config.get("target_roles", "Operations Manager, Facility Manager, Maintenance Manager"),
                            "target_industries": config.get("target_industries", "Manufacturing, Industrial, Automotive"),
                            "target_company_sizes": config.get("target_company_sizes", "51-200, 201-500, 501-1000"),
                            "target_locations": config.get("target_locations", "United States"),
                            "target_seniority": config.get("target_seniority", "Manager, Director, VP, C-Level")
                        }
                    }
                }
        except Exception as e:
            print(f"Error fetching ICP prompt config: {e}")
        
        # Return default prompt if none found
        return {
            "status": "success",
            "data": {
                "prompt": self._get_default_prompt(),
                "default_values": {
                    "target_roles": "Operations Manager, Facility Manager, Maintenance Manager",
                    "target_industries": "Manufacturing, Industrial, Automotive",
                    "target_company_sizes": "51-200, 201-500, 501-1000",
                    "target_locations": "United States",
                    "target_seniority": "Manager, Director, VP, C-Level"
                }
            }
        }

    def update_prompt(self, prompt: str) -> Dict[str, Any]:
        """Update the ICP prompt configuration"""
        try:
            # Check if config exists
            result = self.supabase.table("icp_prompt_config").select("*").limit(1).execute()
            
            if result.data:
                # Update existing config
                self.supabase.table("icp_prompt_config").update({
                    "prompt": prompt,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", result.data[0]["id"]).execute()
            else:
                # Create new config
                self.supabase.table("icp_prompt_config").insert({
                    "prompt": prompt,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).execute()
            
            return {"status": "success", "message": "Prompt updated successfully"}
        except Exception as e:
            print(f"Error updating ICP prompt: {e}")
            return {"status": "error", "message": str(e)}

    def update_default_values(self, default_values: Dict[str, str]) -> Dict[str, Any]:
        """Update the default values for ICP configuration"""
        try:
            # Check if config exists
            result = self.supabase.table("icp_prompt_config").select("*").limit(1).execute()
            
            update_data = {
                "target_roles": default_values.get("target_roles", ""),
                "target_industries": default_values.get("target_industries", ""),
                "target_company_sizes": default_values.get("target_company_sizes", ""),
                "target_locations": default_values.get("target_locations", ""),
                "target_seniority": default_values.get("target_seniority", ""),
                "updated_at": datetime.now().isoformat()
            }
            
            if result.data:
                # Update existing config
                self.supabase.table("icp_prompt_config").update(update_data).eq("id", result.data[0]["id"]).execute()
            else:
                # Create new config
                update_data["created_at"] = datetime.now().isoformat()
                self.supabase.table("icp_prompt_config").insert(update_data).execute()
            
            return {"status": "success", "message": "Default values updated successfully"}
        except Exception as e:
            print(f"Error updating default values: {e}")
            return {"status": "error", "message": str(e)}
    
    def update_prompt_and_values(self, prompt: str, default_values: Dict[str, str]) -> Dict[str, Any]:
        """Update both prompt and default values in a single operation"""
        try:
            # Check if config exists
            result = self.supabase.table("icp_prompt_config").select("*").limit(1).execute()
            
            update_data = {
                "prompt": prompt,
                "target_roles": default_values.get("target_roles", ""),
                "target_industries": default_values.get("target_industries", ""),
                "target_company_sizes": default_values.get("target_company_sizes", ""),
                "target_locations": default_values.get("target_locations", ""),
                "target_seniority": default_values.get("target_seniority", ""),
                "updated_at": datetime.now().isoformat()
            }
            
            if result.data:
                # Update existing config
                self.supabase.table("icp_prompt_config").update(update_data).eq("id", result.data[0]["id"]).execute()
            else:
                # Create new config
                update_data["created_at"] = datetime.now().isoformat()
                self.supabase.table("icp_prompt_config").insert(update_data).execute()
            
            return {"status": "success", "message": "Prompt and default values updated successfully"}
        except Exception as e:
            print(f"Error updating prompt and default values: {e}")
            return {"status": "error", "message": str(e)}

    async def _get_default_config(self) -> Dict[str, Any]:
        """Get default ICP configuration"""
        try:
            result = self.supabase.table("icp_settings").select("*").limit(1).execute()
            if result.data:
                config = result.data[0]
                # Convert to expected format
                return {
                    "target_industries": config.get("target_industries", ["Manufacturing", "Industrial", "Automotive"]),
                    "target_roles": config.get("target_job_titles", ["Operations Manager", "Facility Manager", "Maintenance Manager"]),
                    "company_size_ranges": config.get("target_company_sizes", ["51-200", "201-500", "501-1000"]),
                    "custom_prompt": config.get("custom_prompt", ""),
                    "weights": {
                        "industry_fit": 30,
                        "role_fit": 30,
                        "company_size_fit": 20,
                        "decision_maker": 20
                    }
                }
        except Exception as e:
            print(f"Error fetching ICP config: {e}")
        
        # Return default config if none found
        return {
            "target_industries": ["Manufacturing", "Industrial", "Automotive", "Technology", "Healthcare"],
            "target_roles": ["Operations Manager", "Facility Manager", "Maintenance Manager", "Plant Manager", "Production Manager", "COO", "VP Operations"],
            "company_size_ranges": ["51-200", "201-500", "501-1000", "1001-5000"],
            "custom_prompt": "You are an expert lead qualification analyst. Analyze the LinkedIn profile and score based on industry fit, role relevance, company size, and decision-making authority.",
            "weights": {
                "industry_fit": 30,
                "role_fit": 30,
                "company_size_fit": 20,
                "decision_maker": 20
            }
        }

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
        
        # Track used and exhausted keys
        self.used_keys = set()
        self.exhausted_keys = set()
        
        # Track total available keys
        self.total_keys = len(apify_tokens)
        
        # Google API credentials for search method
        self.google_api_key = getattr(self.settings, 'GOOGLE_API_KEY', None)
        self.google_cse_id = getattr(self.settings, 'GOOGLE_CSE_ID', None)
        
        # Status tracking for polling-based updates
        self.status_sessions = {}
        
        # Initialize AI ICP scorer
        self.ai_icp_scorer = AIICPScorer()
    
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
                # Small delay to ensure frontend has time to start polling
                await asyncio.sleep(0.5)
            
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
                # Calculate ETA (approximately 2-3 seconds per lead)
                estimated_seconds = len(leads) * 2.5
                eta_minutes = int(estimated_seconds // 60)
                eta_seconds = int(estimated_seconds % 60)
                eta_text = f"{eta_minutes}m {eta_seconds}s" if eta_minutes > 0 else f"{eta_seconds}s"
                
                # Emit status update for ICP scoring start
                if session_id:
                    self.emit_status(session_id, {
                        "type": "icp_scoring_started",
                        "message": f"Scoring based on ICP... (ETA: {eta_text})",
                        "total_leads": len(leads),
                        "estimated_duration": estimated_seconds,
                        "eta_text": eta_text,
                        "method": method
                    })
                    # Add delay to ensure frontend can catch this status
                    await asyncio.sleep(1.0)
                
                for idx, lead in enumerate(leads):
                    # AI ICP scoring with new robust implementation
                    try:
                        icp_analysis = await self.ai_icp_scorer.analyze_profile(lead)
                        lead["icp_score"] = icp_analysis["icp_score"]
                        lead["icp_percentage"] = icp_analysis["icp_percentage"]
                        lead["icp_grade"] = icp_analysis["icp_grade"]
                        lead["icp_breakdown"] = icp_analysis["icp_breakdown"]
                    except Exception as e:
                        print(f"Error in AI ICP scoring for lead {idx}: {e}")
                        # Fallback to default scores on error
                        lead["icp_score"] = 50.0
                        lead["icp_percentage"] = 50.0
                        lead["icp_grade"] = "C"
                        error_msg = str(e).replace('{', '{{').replace('}', '}}')
                        lead["icp_breakdown"] = {"reasoning": f"Error in AI scoring: {error_msg}"}
                    
                    # Emit progress update for each scored lead
                    if session_id:
                        self.emit_status(session_id, {
                            "type": "lead_scored",
                            "message": f"Processed lead {idx + 1} of {len(leads)}",
                            "current_lead": idx + 1,
                            "total_leads": len(leads),
                            "method": method
                        })
                        # Add delay to ensure frontend can catch this status
                        await asyncio.sleep(0.3)
                
                # Emit completion status for ICP scoring
                if session_id:
                    self.emit_status(session_id, {
                        "type": "icp_scoring_completed",
                        "message": f"Completed ICP scoring for {len(leads)} leads",
                        "leads_scored": len(leads),
                        "method": method
                    })
                    # Add delay to ensure frontend can catch this status
                    await asyncio.sleep(1.0)
            
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
                
                save_result = await self._save_leads_to_db(leads, params.get("user_id"))
                
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
                # Add delay to ensure frontend can catch the completion status
                await asyncio.sleep(2.0)
                # Session will be automatically cleaned up after 60 seconds
            
            return {
                "status": "success",
                "message": f"Generated {len(leads)} leads" + (f". {save_result['message']}" if save_result else ""),
                "leads": leads,
                "count": len(leads),
                "leads_generated": len(leads),
                "save_stats": save_result.get("stats") if save_result else None
            }
            
        except Exception as e:
            # Emit error status if session_id is available
            if session_id:
                self.emit_status(session_id, {
                    "type": "error",
                    "message": f"Lead generation failed: {str(e).replace('{', '{{').replace('}', '}}')}",
                    "method": method if 'method' in locals() else "unknown"
                })
                # Session will be automatically cleaned up after 60 seconds
            
            return {
                "status": "error",
                "message": f"Lead generation failed: {str(e).replace('{', '{{').replace('}', '}}')}"
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
            
            # Emit Apollo URL to frontend
            if session_id:
                self.emit_status(session_id, {
                    "type": "apollo_url_generated",
                    "message": "Generated Apollo search URL",
                    "apollo_url": apollo_url,
                    "method": "apollo"
                })
            
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
                        "url": apollo_url,
                        "include_email": True,
                        "contact_email_status_v2_verified": True
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
                # Add delay to ensure frontend can catch this status
                await asyncio.sleep(1.0)
            
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
                # Add delay to ensure frontend can catch this status
                await asyncio.sleep(1.0)
            
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
            # Add delay to ensure frontend can catch this status
            await asyncio.sleep(1.0)
        
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
                    # Add delay to ensure frontend can catch this status
                    await asyncio.sleep(0.5)
                
                enriched_profile_list = await self.enrich_profile_with_apify(linkedin_url)
                if enriched_profile_list and len(enriched_profile_list) > 0:
                    enriched_profile = enriched_profile_list[0]  # Get the first (and should be only) profile
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
                        
                        # AI ICP scoring with new implementation
                        try:
                            icp_result = await self.ai_icp_scorer.analyze_profile(enriched_profile)
                            enriched_profile["icp_score"] = icp_result.get("icp_score", 0)
                            enriched_profile["icp_percentage"] = icp_result.get("icp_percentage", 0)
                            enriched_profile["icp_grade"] = icp_result.get("icp_grade", "D")
                            enriched_profile["icp_breakdown"] = icp_result.get("icp_breakdown", {"reasoning": "No breakdown available"})
                            print(f"AI ICP scoring successful for {enriched_profile.get('fullName', 'Unknown')}: {enriched_profile['icp_percentage']}%")
                        except Exception as e:
                            print(f"AI ICP scoring failed for profile: {e}")
                            enriched_profile["icp_score"] = 0
                            enriched_profile["icp_percentage"] = 0
                            enriched_profile["icp_grade"] = "D"
                            enriched_profile["icp_breakdown"] = {"reasoning": "AI ICP scoring failed"}
                        
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
        # Handle case where profile might be a list instead of dict
        if isinstance(profile, list):
            if len(profile) > 0 and isinstance(profile[0], dict):
                profile = profile[0]  # Take the first item if it's a list of dicts
            else:
                return {}  # Return empty dict if list is empty or contains non-dict items
        elif not isinstance(profile, dict):
            return {}  # Return empty dict if profile is neither list nor dict
            
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

    async def _save_leads_to_db(self, leads: List[Dict[str, Any]], user_id: str = None) -> Dict[str, Any]:
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
                    if user_id and "user_id" not in filtered_profile:
                        filtered_profile["user_id"] = user_id
                        
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
        user_id: str,
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
            # Build query with user isolation
            query = self.supabase.table("leads").select("*", count="exact").eq("user_id", user_id)
            
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
    
    async def update_lead(self, user_id: str, lead_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a lead"""
        try:
            # Add updated timestamp
            lead_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("leads").update(lead_data).eq("id", lead_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Lead updated successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error updating lead: {str(e)}")
    
    async def delete_lead(self, user_id: str, lead_id: str) -> Dict[str, Any]:
        """Delete a lead"""
        try:
            result = self.supabase.table("leads").delete().eq("id", lead_id).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": "Lead deleted successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error deleting lead: {str(e)}")
    
    async def bulk_delete_leads(self, user_id: str, lead_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple leads"""
        try:
            result = self.supabase.table("leads").delete().in_("id", lead_ids).eq("user_id", user_id).execute()
            
            return {
                "status": "success",
                "message": f"Deleted {len(lead_ids)} leads successfully"
            }
            
        except Exception as e:
            raise Exception(f"Error deleting leads: {str(e)}")
    
    async def get_metrics(self, user_id: str, time_range: str = "30d") -> Dict[str, Any]:
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
            
            # Fetch all leads for the user
            all_leads_result = self.supabase.table("leads").select("*").eq("user_id", user_id).execute()
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
            emails_available = len([lead for lead in all_leads if lead.get("email") and lead.get("email").strip()])
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
                        "emailsAvailable": emails_available,
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
        print(f"[DEBUG] Creating status session for {session_id}")
        self.status_sessions[session_id] = {
            "created_at": datetime.now(),
            "active": True,
            "status": "initializing",
            "message": "Starting lead generation...",
            "progress": 0,
            "total": 0,
            "completed": False,
            "error": None,
            "status_history": [],  # Track all status updates
            "current_status": {}   # Current status data
        }
        print(f"[DEBUG] Status session created. Active sessions: {list(self.status_sessions.keys())}")
    
    def emit_status(self, session_id: str, status: Dict[str, Any]):
        """Update status for a session"""
        print(f"[DEBUG] emit_status called for session {session_id} with status: {status}")
        if session_id in self.status_sessions:
            # Create timestamped status update
            timestamped_status = {
                "timestamp": datetime.now().isoformat(),
                **status
            }
            
            # Add to status history
            self.status_sessions[session_id]["status_history"].append(timestamped_status)
            
            # Replace current status completely (don't preserve old fields)
            self.status_sessions[session_id]["current_status"] = timestamped_status.copy()
            
            # Update main session fields for backward compatibility
            self.status_sessions[session_id].update(timestamped_status)
            
            # Mark as completed if it's a completion status
            if status.get("type") in ["generation_completed", "error"]:
                self.status_sessions[session_id]["completed"] = True
                self.status_sessions[session_id]["active"] = False
                
            print(f"[DEBUG] Status updated. History length: {len(self.status_sessions[session_id]['status_history'])}")
            print(f"[DEBUG] Current status type: {self.status_sessions[session_id]['current_status'].get('type', 'unknown')}")
        else:
            print(f"[DEBUG] No status session found for session {session_id}")
    
    def get_status(self, session_id: str, include_history: bool = False) -> Dict[str, Any]:
        """Get current status for a session"""
        print(f"[DEBUG] get_status called for session {session_id}, include_history={include_history}")
        
        # Clean up old completed sessions (older than 30 seconds)
        self._cleanup_old_sessions()
        
        if session_id not in self.status_sessions:
            print(f"[DEBUG] No status session found for session {session_id}")
            return {
                "error": "Session not found",
                "status": "not_found"
            }
        
        session_data = self.status_sessions[session_id]
        
        # Convert datetime objects to ISO strings for safe JSON serialization
        def sanitize_value(v):
            if isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, list):
                return [sanitize_value(item) for item in v]
            elif isinstance(v, dict):
                return {k: sanitize_value(val) for k, val in v.items()}
            else:
                return v
        
        # If including history, return the full session data
        if include_history:
            sanitized_data = {k: sanitize_value(v) for k, v in session_data.items()}
            print(f"[DEBUG] Returning full status with {len(sanitized_data.get('status_history', []))} history items")
        else:
            # For real-time polling, return only the current status (not the overwritten main session data)
            current_status = session_data.get("current_status", {})
            if current_status:
                # Use current_status which has the latest update
                sanitized_data = sanitize_value(current_status)
                # Add essential session metadata
                sanitized_data["session_id"] = session_id
                sanitized_data["active"] = session_data.get("active", True)
                sanitized_data["completed"] = session_data.get("completed", False)
                print(f"[DEBUG] Returning current status: {sanitized_data.get('type', 'unknown')}")
            else:
                # Fallback to main session data if current_status is empty
                sanitized_data = {k: sanitize_value(v) for k, v in session_data.items()}
                if "status_history" in sanitized_data:
                    sanitized_data.pop("status_history")
                print(f"[DEBUG] Fallback: returning main session data")
        
        print(f"[DEBUG] Final sanitized_data keys: {list(sanitized_data.keys())}")
        
        # Mark completion timestamp for cleanup later
        if session_data.get("completed", False) and "completion_timestamp" not in session_data:
            session_data["completion_timestamp"] = datetime.now()
            print(f"[DEBUG] Session {session_id} marked for cleanup in 30 seconds")
        
        return sanitized_data
    
    def _cleanup_old_sessions(self):
        """Clean up completed sessions older than 60 seconds"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session_data in self.status_sessions.items():
            if (session_data.get("completed", False) and 
                "completion_timestamp" in session_data and
                (current_time - session_data["completion_timestamp"]).total_seconds() > 300):
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            print(f"[DEBUG] Cleaning up old completed session: {session_id}")
            del self.status_sessions[session_id]
    
    def close_status_session(self, session_id: str):
        """Close and clean up a status tracking session"""
        if session_id in self.status_sessions:
            print(f"[DEBUG] Closing and cleaning up session {session_id}")
            del self.status_sessions[session_id]