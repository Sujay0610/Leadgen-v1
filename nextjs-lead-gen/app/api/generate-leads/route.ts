import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import OpenAI from 'openai'
import { randomUUID } from 'crypto'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
  baseURL: 'https://openrouter.ai/api/v1/',
})

// Apollo.io API configuration
const APOLLO_API_KEY = process.env.APOLLO_API_KEY
const APOLLO_BASE_URL = 'https://api.apollo.io/v1'

// Google Custom Search API configuration
const GOOGLE_API_KEY = process.env.GOOGLE_API_KEY
const GOOGLE_CSE_ID = process.env.GOOGLE_CSE_ID

// Apify configuration
const APIFY_API_TOKENS = process.env.APIFY_API_TOKEN ? 
  (process.env.APIFY_API_TOKEN.startsWith('[') ? 
    JSON.parse(process.env.APIFY_API_TOKEN) : 
    [process.env.APIFY_API_TOKEN]) : []

// Generate Apollo.io search URL
function generateApolloUrl(queryData: any): string {
  const baseUrl = 'https://app.apollo.io/#/people'
  const queryParts: string[] = []

  // Add static parameters
  queryParts.push('sortByField=recommendations_score')
  queryParts.push('sortAscending=false')
  queryParts.push('page=1')

  // Helper function to add array parameters
  function addArrayParams(paramName: string, values: string[]) {
    values.forEach(val => {
      const decodedValue = val.replace('+', ' ')
      queryParts.push(`${paramName}[]=${encodeURIComponent(decodedValue)}`)
    })
  }

  // Process job titles (maps to personTitles[])
  if (queryData.jobTitles && queryData.jobTitles.length > 0) {
    addArrayParams('personTitles', queryData.jobTitles)
  }

  // Process locations (maps to personLocations[])
  if (queryData.locations && queryData.locations.length > 0) {
    addArrayParams('personLocations', queryData.locations)
  }

  // Process business keywords (maps to qOrganizationKeywordTags[])
  if (queryData.industries && queryData.industries.length > 0) {
    addArrayParams('qOrganizationKeywordTags', queryData.industries)
  }

  // Process employee ranges if provided
  if (queryData.companySizes && queryData.companySizes.length > 0) {
    addArrayParams('organizationNumEmployeesRanges', queryData.companySizes)
  }

  // Add static included organization keyword fields
  queryParts.push('includedOrganizationKeywordFields[]=tags')
  queryParts.push('includedOrganizationKeywordFields[]=name')

  // Only add default employee ranges if not already provided
  if (!queryData.companySizes || queryData.companySizes.length === 0) {
    const employeeRanges = [
      "1,10",
      "11,20",
      "21,50",
      "51,100",
      "101,200"
    ]
    addArrayParams('organizationNumEmployeesRanges', employeeRanges)
  }

  // Add keywords if provided
  if (queryData.keywords) {
    queryParts.push(`qKeywords=${encodeURIComponent(queryData.keywords)}`)
  }

  return `${baseUrl}?${queryParts.join('&')}`
}

// Apollo.io lead search using Apify actor
async function searchApolloLeads(query: any) {
  try {
    if (!APIFY_API_TOKENS || APIFY_API_TOKENS.length === 0) {
      throw new Error('Apify API tokens not configured')
    }

    // Generate Apollo URL
    const apolloUrl = generateApolloUrl(query)
    console.log('Generated Apollo URL:', apolloUrl)

    // Use first available Apify token
    const apifyToken = APIFY_API_TOKENS[0]

    // Run Apify actor
    const actorInput = {
      startUrls: [{ url: apolloUrl }],
      maxItems: 25,
      extendOutputFunction: `($) => {
        const result = {};
        return result;
      }`,
      customMapFunction: `(object) => {
        return {
          ...object
        };
      }`
    }

    const runResponse = await fetch(`https://api.apify.com/v2/acts/curious_coder~apollo-io-scraper/runs?token=${apifyToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(actorInput)
    })

    if (!runResponse.ok) {
      throw new Error(`Apify run failed: ${runResponse.status} ${runResponse.statusText}`)
    }

    const runData = await runResponse.json()
    const runId = runData.data.id

    // Wait for completion and get results
    let attempts = 0
    const maxAttempts = 30
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      const statusResponse = await fetch(`https://api.apify.com/v2/acts/curious_coder~apollo-io-scraper/runs/${runId}?token=${apifyToken}`)
      const statusData = await statusResponse.json()
      
      if (statusData.data.status === 'SUCCEEDED') {
        // Get results
        const resultsResponse = await fetch(`https://api.apify.com/v2/datasets/${statusData.data.defaultDatasetId}/items?token=${apifyToken}`)
        const results = await resultsResponse.json()
        
        return results.map((person: any) => ({
          id: randomUUID(),
          firstName: person.firstName || '',
          lastName: person.lastName || '',
          fullName: person.fullName || `${person.firstName || ''} ${person.lastName || ''}`.trim(),
          email: person.email || '',
          jobTitle: person.jobTitle || person.headline || '',
          companyName: person.companyName || '',
          companyIndustry: person.companyIndustry || '',
          companySize: person.companySize || '',
          location: person.location || '',
          linkedin_url: person.linkedinUrl || person.profileUrl || '',
          source: 'apollo',
          createdAt: new Date().toISOString(),
          emailStatus: 'not_sent'
        }))
      } else if (statusData.data.status === 'FAILED') {
        throw new Error('Apify actor run failed')
      }
      
      attempts++
    }
    
    throw new Error('Apify actor run timeout')

  } catch (error) {
    console.error('Apollo search error:', error)
    throw error
  }
}

// Google Search + Apify enrichment function
async function searchGoogleLeads(query: any) {
  try {
    if (!GOOGLE_API_KEY || !GOOGLE_CSE_ID || !APIFY_API_TOKENS || APIFY_API_TOKENS.length === 0) {
      throw new Error('Google API key, CSE ID, or Apify tokens not configured')
    }

    // Build search query for LinkedIn profiles
    const searchTerms = [
      'site:linkedin.com/in/',
      ...(query.jobTitles || []),
      ...(query.locations || []),
      ...(query.keywords ? [query.keywords] : [])
    ]
    
    const searchQuery = searchTerms.join(' ')
    
    // Search Google for LinkedIn profiles
    const searchUrl = `https://www.googleapis.com/customsearch/v1?key=${GOOGLE_API_KEY}&cx=${GOOGLE_CSE_ID}&q=${encodeURIComponent(searchQuery)}&num=10`
    
    const searchResponse = await fetch(searchUrl)
    
    if (!searchResponse.ok) {
      throw new Error(`Google Search API error: ${searchResponse.status} ${searchResponse.statusText}`)
    }
    
    const searchData = await searchResponse.json()
    
    if (!searchData.items || searchData.items.length === 0) {
      return []
    }
    
    // Extract LinkedIn URLs
    const linkedinUrls = searchData.items
      .map((item: any) => item.link)
      .filter((url: string) => url.includes('linkedin.com/in/'))
      .slice(0, 10) // Limit to 10 profiles
    
    if (linkedinUrls.length === 0) {
      return []
    }
    
    // Use first available Apify token
    const apifyToken = APIFY_API_TOKENS[0]
    
    // Use Apify to enrich LinkedIn profiles
    const actorInput = {
      startUrls: linkedinUrls.map((url: string) => ({ url })),
      maxItems: linkedinUrls.length
    }
    
    const runResponse = await fetch(`https://api.apify.com/v2/acts/apify~linkedin-profile-scraper/runs?token=${apifyToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(actorInput)
    })
    
    if (!runResponse.ok) {
      throw new Error(`Apify run failed: ${runResponse.status} ${runResponse.statusText}`)
    }
    
    const runData = await runResponse.json()
    const runId = runData.data.id
    
    // Wait for completion and get results
    let attempts = 0
    const maxAttempts = 30
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      const statusResponse = await fetch(`https://api.apify.com/v2/acts/apify~linkedin-profile-scraper/runs/${runId}?token=${apifyToken}`)
      const statusData = await statusResponse.json()
      
      if (statusData.data.status === 'SUCCEEDED') {
        // Get results
        const resultsResponse = await fetch(`https://api.apify.com/v2/datasets/${statusData.data.defaultDatasetId}/items?token=${apifyToken}`)
        const results = await resultsResponse.json()
        
        return results.map((profile: any) => ({
          id: randomUUID(),
          firstName: profile.firstName || '',
          lastName: profile.lastName || '',
          fullName: profile.fullName || `${profile.firstName || ''} ${profile.lastName || ''}`.trim(),
          email: '', // LinkedIn scraping doesn't provide emails
          jobTitle: profile.headline || profile.position || '',
          companyName: profile.company || '',
          companyIndustry: profile.industry || '',
          companySize: '',
          location: profile.location || '',
          linkedin_url: profile.url || '',
          source: 'google_search',
          createdAt: new Date().toISOString(),
          emailStatus: 'not_sent'
        }))
      } else if (statusData.data.status === 'FAILED') {
        throw new Error('Apify actor run failed')
      }
      
      attempts++
    }
    
    throw new Error('Apify actor run timeout')
    
  } catch (error) {
    console.error('Google search error:', error)
    throw error
  }
}

// ICP Scoring with OpenAI
async function scoreProfile(profile: any) {
  try {
    const prompt = `
Analyze this lead profile and provide an ICP (Ideal Customer Profile) score from 0-100 and a letter grade (A+, A, B+, B, C+, C, D).

Profile:
${JSON.stringify(profile, null, 2)}

Consider these factors:
- Job title relevance to operations/facility management
- Company size and industry fit
- Decision-making authority
- Geographic location
- Company growth indicators

Respond with ONLY a JSON object in this format:
{
  "score": 85,
  "grade": "A",
  "reasoning": "Brief explanation of the score"
}
`

    const response = await openai.chat.completions.create({
      model: 'gpt-4',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3,
      max_tokens: 200
    })

    const content = response.choices[0]?.message?.content

    if (!content) {
      throw new Error('No content in OpenAI response')
    }

    const result = JSON.parse(content)
    return {
      score: result.score || 0,
      grade: result.grade || 'D',
      reasoning: result.reasoning || 'No reasoning provided'
    }
  } catch (error) {
    console.error('ICP scoring error:', error)
    return {
      score: 0,
      grade: 'D',
      reasoning: 'Error during scoring'
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { method, jobTitles, locations, industries, companySizes, limit = 10 } = body

    if (!method || !jobTitles || !locations) {
      return NextResponse.json(
        { status: 'error', message: 'Missing required parameters' },
        { status: 400 }
      )
    }

    let leads = []

    if (method === 'apollo') {
      if (!APIFY_API_TOKENS || APIFY_API_TOKENS.length === 0) {
        return NextResponse.json(
          { status: 'error', message: 'Apify API tokens not configured' },
          { status: 500 }
        )
      }

      leads = await searchApolloLeads({
        jobTitles,
        locations,
        industries: industries || [],
        companySizes: companySizes || [],
        limit
      })
    } else if (method === 'google_apify') {
      if (!GOOGLE_API_KEY || !GOOGLE_CSE_ID || !APIFY_API_TOKENS || APIFY_API_TOKENS.length === 0) {
        return NextResponse.json(
          { status: 'error', message: 'Google or Apify API credentials not configured' },
          { status: 500 }
        )
      }

      leads = await searchGoogleLeads({
        jobTitles,
        locations,
        industries: industries || [],
        limit
      })
    } else {
      return NextResponse.json(
        { status: 'error', message: 'Invalid method specified' },
        { status: 400 }
      )
    }

    // Score leads with ICP
     if (process.env.OPENAI_API_KEY) {
       for (let i = 0; i < leads.length; i++) {
         try {
           const icpResult = await scoreProfile(leads[i])
           leads[i] = {
             ...leads[i],
             icpScore: icpResult.score,
             icpGrade: icpResult.grade,
             icpReasoning: icpResult.reasoning
           }
         } catch (error) {
           console.error('Error scoring lead:', error)
           leads[i] = {
             ...leads[i],
             icpScore: 0,
             icpGrade: 'D',
             icpReasoning: 'Error during scoring'
           }
         }
       }
     }

     // Save leads to Supabase
     if (leads.length > 0) {
       try {
         const { error } = await supabase
           .from('leads')
           .insert(leads)

         if (error) {
           console.error('Supabase insert error:', error)
         }
       } catch (error) {
         console.error('Error saving leads to database:', error)
       }
     }

     return NextResponse.json({
       status: 'success',
       data: {
         leads,
         count: leads.length,
         method,
         timestamp: new Date().toISOString()
       }
     })

   } catch (error) {
     console.error('Lead generation error:', error)
     return NextResponse.json(
       { 
         status: 'error', 
         message: error instanceof Error ? error.message : 'Unknown error occurred',
         timestamp: new Date().toISOString()
       },
       { status: 500 }
     )
   }
 }

 // GET endpoint for testing and configuration
 export async function GET() {
   try {
     const config = {
       apollo_configured: !!APOLLO_API_KEY,
       google_configured: !!GOOGLE_API_KEY && !!GOOGLE_CSE_ID,
       apify_configured: APIFY_API_TOKENS.length > 0,
       openai_configured: !!process.env.OPENAI_API_KEY,
       supabase_configured: !!process.env.NEXT_PUBLIC_SUPABASE_URL && !!process.env.SUPABASE_SERVICE_ROLE_KEY
     }

     return NextResponse.json({
       status: 'success',
       message: 'Lead generation API is running',
       configuration: config,
       available_methods: ['apollo', 'google_apify'],
       timestamp: new Date().toISOString()
     })
   } catch (error) {
     return NextResponse.json(
       { 
         status: 'error', 
         message: 'Configuration check failed',
         timestamp: new Date().toISOString()
       },
       { status: 500 }
     )
   }
  }