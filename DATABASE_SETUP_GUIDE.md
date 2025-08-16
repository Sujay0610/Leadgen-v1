# Lead Generation System - Database Setup Guide

## Overview

This guide will help you set up a fresh Supabase database for the Lead Generation System. The system consists of:

- **Backend**: FastAPI application (`backend/` directory)
- **Frontend**: Next.js application (`nextjs-lead-gen/` directory)
- **Streamlit App**: Main Streamlit application (`main.py`)
- **Database**: Supabase PostgreSQL with vector extensions

## Prerequisites

1. **Supabase Account**: Create a new project at [supabase.com](https://supabase.com)
2. **API Keys**: You'll need OpenAI, Apify, Google Sheets, and Resend API keys
3. **Node.js**: For the Next.js frontend
4. **Python 3.11+**: For the backend and Streamlit app

## Step 1: Create New Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose a project name (e.g., "lead-generation-system")
3. Set a strong database password
4. Wait for the project to be created (usually takes 2-3 minutes)

## Step 2: Run Database Migration

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy the entire contents of `supabase/migrations/00_complete_database_setup.sql`
5. Paste it into the SQL editor
6. Click **Run** to execute the migration

**What this migration creates:**
- `leads` table - Core table for storing lead information
- `email_templates` table - Email templates with vector embeddings
- `email_drafts` table - Draft emails
- `email_campaigns` table - Email campaign management
- `email_events` table - Email tracking events
- `profiles` table - User profiles and authentication
- All necessary indexes for performance
- Row Level Security (RLS) policies
- Vector similarity search functions

## Step 3: Configure Environment Variables

### Backend Configuration

Create/update `backend/.env`:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Email Service (Resend)
RESEND_API_KEY=your-resend-api-key
SENDER_EMAIL=your-verified-sender@yourdomain.com

# Lead Generation APIs
APIFY_API_TOKEN=your-apify-token
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CSE_ID=your-google-cse-id

# Google Sheets (for data export)
GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", ...}'

# Security
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Frontend Configuration

Create/update `nextjs-lead-gen/.env.local`:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# OpenAI (if needed for frontend)
OPENAI_API_KEY=your-openai-api-key
```

### Streamlit Configuration

Create/update `.streamlit/secrets.toml`:

```toml
# Supabase Configuration
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"

# OpenAI Configuration
OPENAI_API_KEY = "your-openai-api-key"

# Lead Generation APIs
APIFY_API_TOKEN = ["your-apify-token-1", "your-apify-token-2"]
GOOGLE_API_KEY = "your-google-api-key"
GOOGLE_CSE_ID = "your-google-cse-id"

# Email Service
RESEND_API_KEY = "your-resend-api-key"
SENDER_EMAIL = "your-verified-sender@yourdomain.com"

# Google Sheets Credentials (JSON as string)
GOOGLE_SHEETS_CREDENTIALS = '{"type": "service_account", "project_id": "your-project", ...}'
```

## Step 4: Get Your Supabase Credentials

1. In your Supabase project dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (use as `SUPABASE_URL`)
   - **anon public** key (use as `SUPABASE_ANON_KEY`)
   - **service_role secret** key (use as `SUPABASE_SERVICE_ROLE_KEY`)

⚠️ **Important**: Keep your `service_role` key secret! Only use it in backend/server environments.

## Step 5: Install Dependencies

### Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Dependencies
```bash
cd nextjs-lead-gen
npm install
```

### Streamlit Dependencies
```bash
pip install -r requirements.txt
```

## Step 6: Start the Applications

### Start Backend (FastAPI)
```bash
cd backend
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Backend will be available at: http://localhost:8000

### Start Frontend (Next.js)
```bash
cd nextjs-lead-gen
npm run dev
```
Frontend will be available at: http://localhost:3000

### Start Streamlit App
```bash
streamlit run main.py
```
Streamlit will be available at: http://localhost:8501

## Step 7: Verify Setup

1. **Database**: Check that all tables were created in Supabase dashboard → Table Editor
2. **Backend**: Visit http://localhost:8000/docs to see the API documentation
3. **Frontend**: Visit http://localhost:3000 to access the web interface
4. **Streamlit**: Visit http://localhost:8501 to access the Streamlit app

## API Keys Setup Guide

### OpenAI API Key
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Add billing information (required for API access)

### Apify API Token
1. Go to [apify.com](https://apify.com)
2. Sign up and get your API token
3. This is used for LinkedIn profile scraping

### Google API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Custom Search API
4. Create credentials (API Key)
5. Set up Custom Search Engine at [cse.google.com](https://cse.google.com)

### Resend API Key
1. Go to [resend.com](https://resend.com)
2. Sign up and verify your domain
3. Get your API key
4. Add your verified sender email

### Google Sheets API
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Google Sheets API
3. Create a Service Account
4. Download the JSON credentials file
5. Convert the JSON to a string for environment variables

## Troubleshooting

### Common Issues

1. **"Could not find column" errors**: Make sure you ran the complete migration script
2. **Authentication errors**: Check your Supabase keys and RLS policies
3. **CORS errors**: Ensure your frontend URL is in the CORS allowed origins
4. **API rate limits**: Some APIs have rate limits, consider using multiple API keys

### Database Issues

- **Reset database**: You can reset your Supabase database and re-run the migration
- **Check logs**: Use Supabase dashboard → Logs to see database errors
- **RLS policies**: Make sure Row Level Security policies are correctly set

### Performance Optimization

- **Indexes**: The migration includes all necessary indexes
- **Vector search**: Ensure pgvector extension is enabled for email template similarity
- **Connection pooling**: Consider using connection pooling for high-traffic scenarios

## Next Steps

1. **Configure ICP Scoring**: Set up your Ideal Customer Profile criteria
2. **Email Templates**: Add your email templates through the interface
3. **Lead Generation**: Start generating leads using the various tools
4. **Email Campaigns**: Set up and run email campaigns
5. **Analytics**: Monitor performance through the dashboard

## Support

If you encounter any issues:
1. Check the application logs
2. Verify all environment variables are set correctly
3. Ensure all API keys are valid and have sufficient credits
4. Check Supabase dashboard for database errors

The system is now ready for lead generation and email automation!