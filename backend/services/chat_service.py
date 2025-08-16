import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client
from openai import OpenAI
from config import get_settings
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
import asyncio

class ChatService:
    """Service for AI-powered chat conversations"""
    
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
        else:
            raise ValueError("OpenAI API key is required for chat service")
            
        # Initialize Langchain LLM
        self.llm = ChatOpenAI(
            model="gpt-5-nano-2025-08-07",
            openai_api_key=self.settings.OPENAI_API_KEY
        )
        
        # Initialize memory for conversation
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize tools and agent
        self._setup_tools_and_agent()
    
    def _setup_tools_and_agent(self):
        """Setup Langchain tools and agent for lead generation"""
        tools = [
            Tool(
                name="apollo_lead_generation",
                description="Generate leads using Apollo.io method. Input should be JSON with jobTitles, locations, industries, and companySizes arrays.",
                func=self._apollo_lead_generation_tool
            ),
            Tool(
                name="google_search_lead_generation",
                description="Generate leads using Google Search + LinkedIn method. Input should be JSON with jobTitles, locations, and industries arrays.",
                func=self._google_search_lead_generation_tool
            ),
            Tool(
                name="method_selector",
                description="Help user choose between Apollo and Google Search methods based on their requirements.",
                func=self._method_selector_tool
            )
        ]
        
        prompt = PromptTemplate.from_template("""
You are Lead Generation Joe, an AI assistant specialized in lead generation and business development.

Your role is to:
1. Help users choose the best lead generation method (Apollo or Google Search)
2. Extract structured information from user queries (job titles, locations, industries, company sizes)
3. Generate high-quality leads based on specific criteria
4. Provide guidance on lead generation best practices

Available methods:
- Apollo: Best for targeted B2B lead generation with detailed filters
- Google Search: Good for finding LinkedIn profiles and broader searches

When a user asks for leads:
1. First determine if they need help choosing a method
2. Extract the required information (job titles, locations, industries)
3. Use the appropriate tool to generate leads
4. Provide helpful insights about the results

STRICT FORMAT RULES:
1. ALWAYS start with "Thought:"
2. Use the format: Thought -> Action -> Action Input -> Observation -> Final Answer
3. Available tools: {tool_names}

Tools available: {tools}

Current conversation:
{chat_history}

Human: {input}
Thought: {agent_scratchpad}
""")
        
        agent = create_react_agent(self.llm, tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory,
            max_iterations=3,
            early_stopping_method="generate"
        )
    
    def _apollo_lead_generation_tool(self, input_str: str) -> str:
        """Tool for Apollo lead generation"""
        try:
            # Parse input JSON
            params = json.loads(input_str)
            
            # Format for lead service
            lead_params = {
                "method": "apollo",
                "jobTitles": params.get("jobTitles", []),
                "locations": params.get("locations", []),
                "industries": params.get("industries", []),
                "companySizes": params.get("companySizes", []),
                "limit": params.get("limit", 10)
            }
            
            # This would call the actual lead service
            # For now, return a structured response
            return json.dumps({
                "method": "apollo",
                "parameters": lead_params,
                "message": f"Apollo lead generation configured for {len(lead_params['jobTitles'])} job titles, {len(lead_params['locations'])} locations, and {len(lead_params['industries'])} industries."
            })
            
        except Exception as e:
            return json.dumps({"error": f"Apollo tool error: {str(e)}"})
    
    def _google_search_lead_generation_tool(self, input_str: str) -> str:
        """Tool for Google Search lead generation"""
        try:
            # Parse input JSON
            params = json.loads(input_str)
            
            # Format for lead service
            lead_params = {
                "method": "google_search",
                "jobTitles": params.get("jobTitles", []),
                "locations": params.get("locations", []),
                "industries": params.get("industries", []),
                "limit": params.get("limit", 10)
            }
            
            return json.dumps({
                "method": "google_search",
                "parameters": lead_params,
                "message": f"Google Search lead generation configured for {len(lead_params['jobTitles'])} job titles and {len(lead_params['locations'])} locations."
            })
            
        except Exception as e:
            return json.dumps({"error": f"Google Search tool error: {str(e)}"})
    
    def _method_selector_tool(self, input_str: str) -> str:
        """Tool to help users choose between methods"""
        return json.dumps({
            "apollo": {
                "description": "Best for targeted B2B lead generation with detailed company and employee filters",
                "pros": ["Detailed company data", "Employee count filters", "Industry targeting"],
                "cons": ["May have usage limits", "Requires specific criteria"]
            },
            "google_search": {
                "description": "Good for finding LinkedIn profiles through search",
                "pros": ["Broader search capability", "LinkedIn profile discovery"],
                "cons": ["Less structured data", "May require more filtering"]
            },
            "recommendation": "Choose Apollo for targeted B2B campaigns, Google Search for broader LinkedIn prospecting"
        })
    
    async def process_chat_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process chat message using Langchain agent"""
        try:
            message = params.get("message", "")
            conversation_history = params.get("conversationHistory", [])
            context = params.get("context", {})
            
            if not message:
                return {
                    "status": "error",
                    "message": "Message is required"
                }
            
            # Add conversation history to memory
            for msg in conversation_history[-5:]:  # Keep last 5 messages
                if msg.get("role") == "user":
                    self.memory.chat_memory.add_user_message(msg.get("content", ""))
                elif msg.get("role") == "assistant":
                    self.memory.chat_memory.add_ai_message(msg.get("content", ""))
            
            # Temporary bypass of Langchain agent - use direct OpenAI API
            # Build conversation messages
            messages = [
                {"role": "system", "content": "You are Lead Generation Joe, an AI assistant specialized in lead generation and business development. Help users with lead generation queries, extract job titles, locations, and industries from their requests."}
            ]
            
            # Add conversation history
            for msg in conversation_history[-5:]:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg.get("role"),
                        "content": msg.get("content", "")
                    })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Call OpenAI directly
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=messages
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Extract structured data if present
            structured_data = self._extract_structured_data(ai_response)
            
            # Save conversation to database
            conversation_id = await self._save_conversation(
                message, ai_response, context, structured_data
            )
            
            return {
                "status": "success",
                "data": {
                    "response": ai_response,
                    "conversationId": conversation_id,
                    "structuredData": structured_data,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Chat processing failed: {str(e)}"
            }
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt based on context"""
        base_prompt = """
You are Lead Generation Joe, a specialized AI assistant focused exclusively on lead generation and prospecting. Your primary goal is to help users generate high-quality leads by collecting specific criteria and then automatically triggering lead scraping.

Your conversation flow should be:
1. Greet the user warmly and ask what type of leads they're looking for
2. Systematically collect the following required parameters:
   - Target Industries (e.g., "SaaS", "Manufacturing", "Healthcare", "E-commerce")
   - Geographic Locations (cities, states, countries - e.g., "San Francisco", "New York", "United States")
   - Target Job Titles/Roles (e.g., "CEO", "VP of Sales", "Marketing Manager", "Operations Director")
   - Company Size (e.g., "1-50", "51-200", "201-1000", "1000+")

3. Once you have all four parameters, immediately format them as JSON in this exact structure:
{
  "jobTitles": ["title1", "title2"],
  "locations": ["location1", "location2"],
  "industries": ["industry1", "industry2"],
  "companySizes": ["size1", "size2"]
}

IMPORTANT BEHAVIOR:
- Always ask for missing parameters one at a time in a conversational way
- Be specific about what you need (don't accept vague answers)
- Once you have all 4 parameters, include the JSON structure in your response
- Keep responses concise and focused on lead generation
- Don't provide general business advice - stay focused on lead generation

Example conversation:
"Hi! I'm Lead Generation Joe. I'll help you find the perfect leads for your business. What industry are you targeting?"

User: "SaaS companies"

"Great! SaaS is a fantastic space. What geographic locations should I focus on?"

User: "San Francisco and New York"

"Perfect! Now, what job titles or roles are you looking to connect with?"

User: "CEOs and VP of Sales"

"Excellent! Finally, what company size range works best for you?"

User: "50-200 employees"

"Perfect! I have everything I need. Let me generate leads for SaaS companies in San Francisco and New York, targeting CEOs and VPs of Sales at companies with 50-200 employees.

{
  \"jobTitles\": [\"CEO\", \"VP of Sales\"],
  \"locations\": [\"San Francisco\", \"New York\"],
  \"industries\": [\"SaaS\"],
  \"companySizes\": [\"51-200\"]
}"

Be friendly, efficient, and laser-focused on collecting these parameters to generate leads.
"""
        
        return base_prompt
    
    def _extract_structured_data(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON data from AI response"""
        try:
            # Look for JSON blocks in the response
            import re
            
            # Try to find JSON blocks
            json_pattern = r'```json\s*({.*?})\s*```'
            json_matches = re.findall(json_pattern, response, re.DOTALL)
            
            if json_matches:
                return json.loads(json_matches[0])
            
            # Try to find inline JSON
            json_pattern = r'{[^{}]*(?:{[^{}]*}[^{}]*)*}'
            json_matches = re.findall(json_pattern, response)
            
            for match in json_matches:
                try:
                    parsed = json.loads(match)
                    # Check if it looks like lead generation parameters
                    if any(key in parsed for key in ['jobTitles', 'locations', 'industries', 'companySizes']):
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _extract_structured_data_from_agent_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract structured data from Langchain agent result"""
        try:
            # Check if the agent used any tools that returned structured data
            output = result.get("output", "")
            
            # Try to extract JSON from the output
            structured_data = self._extract_structured_data(output)
            if structured_data:
                return structured_data
            
            # Check intermediate steps for tool outputs
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    try:
                        # Try to parse observation as JSON
                        tool_result = json.loads(observation)
                        if "parameters" in tool_result:
                            return tool_result["parameters"]
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            return None
            
        except Exception:
            return None
    
    async def _save_conversation(self, user_message: str, ai_response: str, 
                               context: Dict[str, Any], structured_data: Optional[Dict[str, Any]]) -> str:
        """Save conversation to database"""
        try:
            conversation_id = str(uuid.uuid4())
            
            # Skip database save for now since table doesn't exist
            # Just return a UUID
            return conversation_id
            
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return str(uuid.uuid4())  # Return a UUID even if save fails
    
    async def get_conversation_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent conversation history"""
        try:
            result = self.supabase.table("chat_conversations").select("*").order("created_at", ascending=False).limit(limit).execute()
            
            return {
                "status": "success",
                "data": result.data or []
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error fetching conversation history: {str(e)}"
            }
    
    async def generate_lead_suggestions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate lead generation suggestions based on user input"""
        try:
            industry = params.get("industry", "")
            company_size = params.get("companySize", "")
            location = params.get("location", "")
            goals = params.get("goals", "")
            
            prompt = f"""
Based on the following business context, suggest optimal lead generation parameters:

Industry: {industry}
Company Size: {company_size}
Location: {location}
Goals: {goals}

Provide suggestions for:
1. Target job titles (5-8 specific titles)
2. Relevant industries (if different from specified)
3. Optimal company sizes
4. Geographic targeting recommendations
5. Key messaging themes for outreach

Format your response as JSON with the following structure:
{{
    "jobTitles": ["title1", "title2", ...],
    "industries": ["industry1", "industry2", ...],
    "companySizes": ["size1", "size2", ...],
    "locations": ["location1", "location2", ...],
    "messagingThemes": ["theme1", "theme2", ...],
    "reasoning": "Explanation of recommendations"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are a lead generation expert. Provide specific, actionable recommendations."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            structured_data = self._extract_structured_data(ai_response)
            
            if not structured_data:
                # Try to parse the entire response as JSON
                try:
                    structured_data = json.loads(ai_response)
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "message": "Failed to parse AI suggestions"
                    }
            
            return {
                "status": "success",
                "data": structured_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating suggestions: {str(e)}"
            }
    
    async def analyze_lead_quality(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze lead quality using AI"""
        try:
            prompt = f"""
Analyze the quality of this lead and provide insights:

Lead Data:
{json.dumps(lead_data, indent=2)}

Provide analysis on:
1. Lead quality score (1-10)
2. Strengths and opportunities
3. Recommended approach for outreach
4. Potential objections and how to address them
5. Best time/method for contact

Format as JSON:
{{
    "qualityScore": <1-10>,
    "strengths": ["strength1", "strength2", ...],
    "opportunities": ["opp1", "opp2", ...],
    "outreachStrategy": "recommended approach",
    "potentialObjections": ["objection1", "objection2", ...],
    "contactRecommendations": "best practices for contact",
    "reasoning": "detailed analysis"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are a sales expert specializing in lead qualification and outreach strategy."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            structured_data = self._extract_structured_data(ai_response)
            
            if not structured_data:
                try:
                    structured_data = json.loads(ai_response)
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "message": "Failed to parse lead analysis"
                    }
            
            return {
                "status": "success",
                "data": structured_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error analyzing lead: {str(e)}"
            }
    
    async def generate_outreach_sequence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a multi-touch outreach sequence"""
        try:
            lead_info = params.get("leadInfo", {})
            sequence_type = params.get("sequenceType", "cold_outreach")
            num_touches = params.get("numTouches", 3)
            
            prompt = f"""
Create a {num_touches}-touch outreach sequence for this lead:

Lead Information:
{json.dumps(lead_info, indent=2)}

Sequence Type: {sequence_type}

For each touch, provide:
1. Timing (days after previous touch)
2. Channel (email, LinkedIn, phone)
3. Subject line (for emails)
4. Message content
5. Call-to-action

Format as JSON:
{{
    "sequence": [
        {{
            "touchNumber": 1,
            "timing": "immediate",
            "channel": "email",
            "subject": "subject line",
            "content": "message content",
            "callToAction": "specific CTA"
        }},
        ...
    ],
    "strategy": "overall sequence strategy",
    "expectedOutcome": "what to expect from this sequence"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert in sales outreach sequences and multi-touch campaigns."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            structured_data = self._extract_structured_data(ai_response)
            
            if not structured_data:
                try:
                    structured_data = json.loads(ai_response)
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "message": "Failed to parse outreach sequence"
                    }
            
            return {
                "status": "success",
                "data": structured_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating outreach sequence: {str(e)}"
            }