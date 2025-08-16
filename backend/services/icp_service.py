import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client
from openai import OpenAI
from config import get_settings

class ICPService:
    """Service for ICP (Ideal Customer Profile) management and scoring"""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Initialize OpenAI client for AI-powered ICP analysis
        if self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
    
    async def get_icp_configurations(self) -> Dict[str, Any]:
        """Get all ICP configurations"""
        try:
            result = self.supabase.table("icp_configurations").select("*").order("created_at", ascending=False).execute()
            
            return {
                "status": "success",
                "data": result.data or []
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching ICP configurations: {str(e)}"
            }
    
    async def create_icp_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new ICP configuration"""
        try:
            config = {
                "id": str(uuid.uuid4()),
                "name": config_data.get("name"),
                "description": config_data.get("description", ""),
                "criteria": config_data.get("criteria", {}),
                "weights": config_data.get("weights", {
                    "industry_fit": 30,
                    "role_fit": 30,
                    "company_size_fit": 20,
                    "decision_maker": 20
                }),
                "target_industries": config_data.get("targetIndustries", []),
                "target_roles": config_data.get("targetRoles", []),
                "company_size_ranges": config_data.get("companySizeRanges", []),
                "geographic_preferences": config_data.get("geographicPreferences", []),
                "technology_stack": config_data.get("technologyStack", []),
                "minimum_score_threshold": config_data.get("minimumScoreThreshold", 50),
                "is_active": config_data.get("isActive", True),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("icp_configurations").insert(config).execute()
            
            return {
                "status": "success",
                "message": "ICP configuration created successfully",
                "data": config
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating ICP configuration: {str(e)}"
            }
    
    async def update_icp_configuration(self, config_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update ICP configuration"""
        try:
            config_data["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("icp_configurations").update(config_data).eq("id", config_id).execute()
            
            return {
                "status": "success",
                "message": "ICP configuration updated successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating ICP configuration: {str(e)}"
            }
    
    async def delete_icp_configuration(self, config_id: str) -> Dict[str, Any]:
        """Delete ICP configuration"""
        try:
            result = self.supabase.table("icp_configurations").delete().eq("id", config_id).execute()
            
            return {
                "status": "success",
                "message": "ICP configuration deleted successfully"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting ICP configuration: {str(e)}"
            }
    
    async def score_lead_against_icp(self, lead_data: Dict[str, Any], config_id: str = None) -> Dict[str, Any]:
        """Score a lead against ICP configuration"""
        try:
            # Get ICP configuration
            if config_id:
                config_result = self.supabase.table("icp_configurations").select("*").eq("id", config_id).execute()
                if not config_result.data:
                    return {
                        "status": "error",
                        "message": "ICP configuration not found"
                    }
                config = config_result.data[0]
            else:
                # Use default active configuration
                config_result = self.supabase.table("icp_configurations").select("*").eq("is_active", True).limit(1).execute()
                if not config_result.data:
                    return {
                        "status": "error",
                        "message": "No active ICP configuration found"
                    }
                config = config_result.data[0]
            
            # Calculate scores
            scores = self._calculate_icp_scores(lead_data, config)
            
            # Calculate weighted total score
            weights = config.get("weights", {})
            total_score = (
                scores["industry_fit"] * weights.get("industry_fit", 25) / 100 +
                scores["role_fit"] * weights.get("role_fit", 25) / 100 +
                scores["company_size_fit"] * weights.get("company_size_fit", 25) / 100 +
                scores["decision_maker"] * weights.get("decision_maker", 25) / 100
            )
            
            # Convert to percentage
            score_percentage = min(100, total_score * 10)
            
            # Determine grade
            grade = self._calculate_grade(score_percentage)
            
            # Determine ICP category
            icp_category = self._determine_icp_category(lead_data, config, score_percentage)
            
            # Generate reasoning
            reasoning = self._generate_scoring_reasoning(lead_data, config, scores)
            
            result = {
                "total_score": round(total_score, 2),
                "score_percentage": round(score_percentage, 2),
                "grade": grade,
                "breakdown": {
                    "industry_fit": scores["industry_fit"],
                    "role_fit": scores["role_fit"],
                    "company_size_fit": scores["company_size_fit"],
                    "decision_maker": scores["decision_maker"],
                    "icp_category": icp_category,
                    "reasoning": reasoning
                },
                "config_used": config["name"],
                "meets_threshold": score_percentage >= config.get("minimum_score_threshold", 50)
            }
            
            return {
                "status": "success",
                "data": result
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error scoring lead: {str(e)}"
            }
    
    def _calculate_icp_scores(self, lead_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, float]:
        """Calculate individual ICP scores"""
        scores = {
            "industry_fit": 0.0,
            "role_fit": 0.0,
            "company_size_fit": 0.0,
            "decision_maker": 0.0
        }
        
        # Industry fit scoring
        lead_industry = lead_data.get("companyIndustry", "").lower()
        target_industries = [ind.lower() for ind in config.get("target_industries", [])]
        
        if lead_industry and target_industries:
            # Exact match
            if lead_industry in target_industries:
                scores["industry_fit"] = 10.0
            else:
                # Partial match (contains keywords)
                for target in target_industries:
                    if target in lead_industry or lead_industry in target:
                        scores["industry_fit"] = max(scores["industry_fit"], 7.0)
                        break
        
        # Role fit scoring
        lead_title = lead_data.get("jobTitle", "").lower()
        lead_headline = lead_data.get("headline", "").lower()
        target_roles = [role.lower() for role in config.get("target_roles", [])]
        
        if target_roles:
            for target_role in target_roles:
                if target_role in lead_title or target_role in lead_headline:
                    scores["role_fit"] = 10.0
                    break
                # Check for partial matches
                role_keywords = target_role.split()
                if any(keyword in lead_title or keyword in lead_headline for keyword in role_keywords):
                    scores["role_fit"] = max(scores["role_fit"], 6.0)
        
        # Company size fit scoring
        lead_company_size = lead_data.get("companySize", "")
        target_sizes = config.get("company_size_ranges", [])
        
        if lead_company_size and target_sizes:
            if lead_company_size in target_sizes:
                scores["company_size_fit"] = 10.0
            else:
                # Try to match size ranges
                scores["company_size_fit"] = self._match_company_size(lead_company_size, target_sizes)
        
        # Decision maker scoring
        seniority = lead_data.get("seniority", "").lower()
        functions = lead_data.get("functions", "").lower()
        
        # Check for leadership indicators
        leadership_keywords = [
            "director", "manager", "head", "lead", "chief", "vp", "vice president",
            "senior", "principal", "owner", "founder", "executive", "supervisor"
        ]
        
        decision_score = 0.0
        for keyword in leadership_keywords:
            if keyword in lead_title or keyword in seniority or keyword in functions:
                if keyword in ["chief", "vp", "vice president", "director", "head"]:
                    decision_score = 10.0
                    break
                elif keyword in ["manager", "lead", "senior", "principal"]:
                    decision_score = max(decision_score, 7.0)
                else:
                    decision_score = max(decision_score, 5.0)
        
        scores["decision_maker"] = decision_score
        
        return scores
    
    def _match_company_size(self, lead_size: str, target_sizes: List[str]) -> float:
        """Match company size ranges"""
        # Simple size matching logic
        size_mappings = {
            "1-10": ["1-10", "startup", "small"],
            "11-50": ["11-50", "small"],
            "51-200": ["51-200", "medium"],
            "201-500": ["201-500", "medium"],
            "501-1000": ["501-1000", "large"],
            "1001-5000": ["1001-5000", "large"],
            "5001+": ["5001+", "enterprise", "large"]
        }
        
        for target_size in target_sizes:
            if target_size.lower() in lead_size.lower():
                return 10.0
            
            # Check mappings
            if target_size in size_mappings:
                for mapping in size_mappings[target_size]:
                    if mapping in lead_size.lower():
                        return 8.0
        
        return 3.0  # Default low score for size mismatch
    
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
    
    def _determine_icp_category(self, lead_data: Dict[str, Any], config: Dict[str, Any], score: float) -> str:
        """Determine ICP category based on lead data and score"""
        if score < 50:
            return "none"
        
        # Simple category determination based on industry
        industry = lead_data.get("companyIndustry", "").lower()
        
        operations_industries = [
            "manufacturing", "industrial", "automation", "equipment", "cnc", 
            "robotics", "facility", "fleet", "operations"
        ]
        
        field_service_industries = [
            "kitchen", "restaurant", "food", "real estate", "appliance", 
            "hotel", "hospitality", "service", "maintenance"
        ]
        
        for ops_industry in operations_industries:
            if ops_industry in industry:
                return "operations"
        
        for fs_industry in field_service_industries:
            if fs_industry in industry:
                return "field_service"
        
        return "general"
    
    def _generate_scoring_reasoning(self, lead_data: Dict[str, Any], config: Dict[str, Any], scores: Dict[str, float]) -> str:
        """Generate human-readable reasoning for the score"""
        reasoning_parts = []
        
        # Industry reasoning
        if scores["industry_fit"] >= 8:
            reasoning_parts.append(f"Strong industry match with {lead_data.get('companyIndustry', 'target industry')}")
        elif scores["industry_fit"] >= 5:
            reasoning_parts.append(f"Partial industry alignment with {lead_data.get('companyIndustry', 'industry')}")
        else:
            reasoning_parts.append("Limited industry fit")
        
        # Role reasoning
        if scores["role_fit"] >= 8:
            reasoning_parts.append(f"Excellent role match: {lead_data.get('jobTitle', 'job title')}")
        elif scores["role_fit"] >= 5:
            reasoning_parts.append(f"Good role alignment: {lead_data.get('jobTitle', 'job title')}")
        else:
            reasoning_parts.append("Role doesn't strongly align with targets")
        
        # Company size reasoning
        if scores["company_size_fit"] >= 8:
            reasoning_parts.append(f"Company size ({lead_data.get('companySize', 'unknown')}) fits target criteria")
        elif scores["company_size_fit"] >= 5:
            reasoning_parts.append(f"Company size ({lead_data.get('companySize', 'unknown')}) partially matches")
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
    
    async def bulk_score_leads(self, lead_ids: List[str], config_id: str = None) -> Dict[str, Any]:
        """Score multiple leads against ICP configuration"""
        try:
            # Get leads
            leads_result = self.supabase.table("leads").select("*").in_("id", lead_ids).execute()
            leads = leads_result.data or []
            
            if not leads:
                return {
                    "status": "error",
                    "message": "No leads found"
                }
            
            scored_leads = []
            
            for lead in leads:
                score_result = await self.score_lead_against_icp(lead, config_id)
                
                if score_result["status"] == "success":
                    lead_with_score = lead.copy()
                    lead_with_score["icp_analysis"] = score_result["data"]
                    scored_leads.append(lead_with_score)
                    
                    # Update lead in database with new scores
                    score_data = score_result["data"]
                    self.supabase.table("leads").update({
                        "icp_score": score_data["score_percentage"],
                        "icp_grade": score_data["grade"],
                        "icp_breakdown": score_data["breakdown"],
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", lead["id"]).execute()
            
            return {
                "status": "success",
                "message": f"Scored {len(scored_leads)} leads successfully",
                "data": scored_leads
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error bulk scoring leads: {str(e)}"
            }
    
    async def get_icp_analytics(self, config_id: str = None, time_range: str = "30d") -> Dict[str, Any]:
        """Get ICP analytics and insights"""
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
            
            # Get leads with ICP scores
            leads_result = self.supabase.table("leads").select("*").gte("created_at", start_date.isoformat()).execute()
            leads = leads_result.data or []
            
            # Calculate analytics
            total_leads = len(leads)
            scored_leads = [lead for lead in leads if lead.get("icp_score") is not None]
            
            if not scored_leads:
                return {
                    "status": "success",
                    "data": {
                        "overview": {
                            "totalLeads": total_leads,
                            "scoredLeads": 0,
                            "averageScore": 0,
                            "highQualityLeads": 0
                        },
                        "distribution": {},
                        "trends": {}
                    }
                }
            
            scores = [lead["icp_score"] for lead in scored_leads]
            average_score = sum(scores) / len(scores)
            high_quality_leads = len([lead for lead in scored_leads if lead["icp_score"] >= 70])
            
            # Grade distribution
            grades = [lead.get("icp_grade", "D") for lead in scored_leads]
            grade_distribution = {}
            for grade in grades:
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
            
            # Score ranges
            score_ranges = {
                "90-100": len([s for s in scores if s >= 90]),
                "80-89": len([s for s in scores if 80 <= s < 90]),
                "70-79": len([s for s in scores if 70 <= s < 80]),
                "60-69": len([s for s in scores if 60 <= s < 70]),
                "50-59": len([s for s in scores if 50 <= s < 60]),
                "0-49": len([s for s in scores if s < 50])
            }
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "totalLeads": total_leads,
                        "scoredLeads": len(scored_leads),
                        "averageScore": round(average_score, 2),
                        "highQualityLeads": high_quality_leads,
                        "qualityRate": round(high_quality_leads / len(scored_leads) * 100, 2) if scored_leads else 0
                    },
                    "distribution": {
                        "grades": grade_distribution,
                        "scoreRanges": score_ranges
                    },
                    "timeRange": time_range
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching ICP analytics: {str(e)}"
            }
    
    async def get_config(self) -> Dict[str, Any]:
        """Get ICP configuration settings"""
        try:
            # Get the first active configuration or return default
            result = self.supabase.table("icp_configurations").select("*").eq("is_active", True).limit(1).execute()
            
            if result.data:
                config = result.data[0]
                return {
                    "status": "success",
                    "data": {
                        "scoringCriteria": config.get("criteria", {}),
                        "targetingRules": {
                            "industries": config.get("target_industries", []),
                            "jobTitles": config.get("target_roles", []),
                            "companySizes": config.get("company_size_ranges", []),
                            "locations": config.get("geographic_preferences", [])
                        },
                        "customPrompt": config.get("description", ""),
                        "weights": config.get("weights", {}),
                        "minimumScoreThreshold": config.get("minimum_score_threshold", 50)
                    }
                }
            else:
                # Return default configuration
                return {
                    "status": "success",
                    "data": {
                        "scoringCriteria": {
                            "jobTitle": {"enabled": True, "weight": 25},
                            "companySize": {"enabled": True, "weight": 20},
                            "industry": {"enabled": True, "weight": 20},
                            "location": {"enabled": True, "weight": 15},
                            "experience": {"enabled": True, "weight": 10},
                            "education": {"enabled": False, "weight": 5},
                            "skills": {"enabled": False, "weight": 5}
                        },
                        "targetingRules": {
                            "industries": ["Manufacturing", "Industrial", "Automotive"],
                            "jobTitles": ["Operations Manager", "Facility Manager", "Maintenance Manager"],
                            "companySizes": ["51-200", "201-500", "501-1000"],
                            "locations": ["United States", "Canada", "United Kingdom"]
                        },
                        "customPrompt": "",
                        "weights": {
                            "industry_fit": 30,
                            "role_fit": 30,
                            "company_size_fit": 20,
                            "decision_maker": 20
                        },
                        "minimumScoreThreshold": 50
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching ICP config: {str(e)}"
            }
    
    async def update_config(self, request_data) -> Dict[str, Any]:
        """Update ICP configuration settings"""
        try:
            # Extract data from request
            config_data = {
                "criteria": getattr(request_data, 'scoringCriteria', {}),
                "target_industries": getattr(request_data, 'targetingRules', {}).get('industries', []),
                "target_roles": getattr(request_data, 'targetingRules', {}).get('jobTitles', []),
                "company_size_ranges": getattr(request_data, 'targetingRules', {}).get('companySizes', []),
                "geographic_preferences": getattr(request_data, 'targetingRules', {}).get('locations', []),
                "description": getattr(request_data, 'customPrompt', ''),
                "weights": getattr(request_data, 'weights', {}),
                "minimum_score_threshold": getattr(request_data, 'minimumScoreThreshold', 50),
                "updated_at": datetime.now().isoformat()
            }
            
            # Check if configuration exists
            result = self.supabase.table("icp_configurations").select("id").eq("is_active", True).limit(1).execute()
            
            if result.data:
                # Update existing configuration
                config_id = result.data[0]['id']
                update_result = self.supabase.table("icp_configurations").update(config_data).eq("id", config_id).execute()
                
                return {
                    "status": "success",
                    "message": "ICP configuration updated successfully",
                    "data": config_data
                }
            else:
                # Create new configuration
                config_data.update({
                    "id": str(uuid.uuid4()),
                    "name": "Default ICP Configuration",
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                })
                
                create_result = self.supabase.table("icp_configurations").insert(config_data).execute()
                
                return {
                    "status": "success",
                    "message": "ICP configuration created successfully",
                    "data": config_data
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating ICP config: {str(e)}"
            }