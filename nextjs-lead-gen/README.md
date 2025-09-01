# Next.js Lead Generation Application

A modern lead generation platform built with Next.js, featuring conversational AI, email automation, and comprehensive analytics.

## Features

- **Dual Lead Generation Methods**:
  - Apollo.io integration via Apify scraping
  - Google Search + LinkedIn enrichment via Apify
- **AI-Powered ICP Scoring**: OpenAI-based lead qualification
- **Conversational Interface**: Chat-based lead generation queries
- **Email Automation**: Template management, campaigns, and tracking
- **Analytics Dashboard**: Comprehensive metrics and insights
- **Real-time Webhooks**: Email event tracking via Resend

## Prerequisites

- Node.js 18+ and npm
- Supabase account and database
- API keys for:
  - OpenAI (for ICP scoring)
  - Apify (for lead scraping)
  - Google Custom Search (optional)
  - Resend (for email sending)
  - Apollo.io (optional)

## Installation

1. **Clone and navigate to the project**:
   ```bash
   cd nextjs-lead-gen
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env.local
   ```
   
   Edit `.env.local` with your actual API keys and configuration:
   ```env
   # Required
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   OPENAI_API_KEY=your_openai_key
   APIFY_API_TOKEN=your_apify_token
   RESEND_API_KEY=your_resend_key
   
   # Optional
   GOOGLE_API_KEY=your_google_key
   GOOGLE_CSE_ID=your_cse_id
   APOLLO_API_KEY=your_apollo_key
   ```

4. **Set up Supabase database**:
   - Run the migration files in `../supabase/migrations/` in your Supabase SQL editor
   - Ensure all tables are created: `leads`, `email_events`, `email_templates`, `email_drafts`, `email_campaigns`, `icp_settings`

## Running the Application

### Development Mode
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build
```bash
npm run build
npm start
```

## API Endpoints

### Lead Generation
- `POST /api/generate-leads` - Generate leads using Apollo.io or Google Search
- `GET /api/generate-leads` - Check API configuration status

### Lead Management
- `GET /api/leads` - Retrieve leads with filtering and pagination
- `POST /api/leads` - Bulk operations (update/delete)
- `PUT /api/leads` - Update individual lead
- `DELETE /api/leads` - Delete individual lead

### Analytics
- `GET /api/leads/metrics` - Lead statistics and breakdowns
- `GET /api/email/dashboard` - Email campaign analytics

### Email System
- `POST /api/email/send` - Send individual emails
- `GET /api/email/send` - Check email status and history
- `GET/POST/PUT/DELETE /api/email/templates` - Template management
- `GET/POST/PUT/DELETE /api/email/campaigns` - Campaign management
- `GET/POST/PUT/DELETE /api/email/drafts` - Draft management

### Configuration
- `GET/POST/PUT /api/icp` - ICP scoring configuration
- `POST /api/chat` - Conversational lead generation
- `POST /api/webhook` - Resend email event webhooks

## Usage

1. **Configure ICP Settings**: Visit `/icp` to set up your ideal customer profile criteria
2. **Generate Leads**: Use `/leads` to search for prospects using Apollo.io or Google Search
3. **Manage Email Templates**: Create and customize email templates in `/email`
4. **Send Campaigns**: Set up and launch email campaigns
5. **Monitor Analytics**: Track performance in `/dashboard`
6. **Chat Interface**: Use conversational queries for lead generation

## Architecture

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and React components
- **Backend**: Next.js API routes with serverless functions
- **Database**: Supabase (PostgreSQL) with real-time subscriptions
- **AI Integration**: OpenAI GPT-5-nano-2025-08-07 for lead scoring and chat responses
- **Email Service**: Resend for transactional emails and webhooks
- **Lead Sources**: Apollo.io and Google Search via Apify actors

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `OPENAI_API_KEY` | Yes | OpenAI API key for ICP scoring |
| `APIFY_API_TOKEN` | Yes | Apify token for lead scraping |
| `RESEND_API_KEY` | Yes | Resend API key for emails |
| `GOOGLE_API_KEY` | No | Google Custom Search API key |
| `GOOGLE_CSE_ID` | No | Google Custom Search Engine ID |
| `APOLLO_API_KEY` | No | Apollo.io API key (legacy) |
| `RESEND_WEBHOOK_SECRET` | No | Resend webhook secret for verification |

## Troubleshooting

- **Database Connection Issues**: Verify Supabase URL and service role key
- **API Rate Limits**: Check your API quotas for OpenAI, Apify, and other services
- **Email Delivery**: Ensure Resend API key is valid and domain is verified
- **Lead Generation Failures**: Verify Apify tokens and actor availability

## Support

For issues and questions, check the API status endpoints or review the browser console for detailed error messages.