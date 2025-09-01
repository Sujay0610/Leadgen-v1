# Lead Generation System

A comprehensive lead generation and email automation system with AI-powered ICP scoring, built with FastAPI, Next.js, and Streamlit.

## 🏗️ Project Structure

```
leadgensupa/
├── backend/                 # FastAPI backend API
│   ├── main.py             # FastAPI application
│   ├── models.py           # Pydantic models
│   ├── config.py           # Configuration settings
│   ├── services/           # Business logic services
│   ├── routes/             # API route handlers
│   └── dependencies/       # Authentication & dependencies
├── nextjs-lead-gen/        # Next.js frontend application
│   ├── app/                # Next.js 14 app directory
│   ├── components/         # React components
│   ├── lib/                # Utility libraries
│   └── package.json        # Frontend dependencies
├── supabase/               # Database migrations
│   └── migrations/         # SQL migration files
├── main.py                 # Streamlit application
├── simple_email_manager.py # Email management utilities
└── .streamlit/             # Streamlit configuration
```

## 🚀 Features

### Lead Generation
- **LinkedIn Profile Scraping** via Apify
- **Apollo.io Integration** for contact enrichment
- **Google Search** for additional lead discovery
- **AI-Powered ICP Scoring** using OpenAI GPT-5-nano-2025-08-07

### Email Automation
- **Template Management** with vector similarity search
- **Personalized Email Generation** using AI
- **Campaign Management** and scheduling
- **Email Event Tracking** (opens, clicks, bounces)
- **Resend Integration** for reliable email delivery

### User Interfaces
- **Next.js Web App** - Modern React-based dashboard
- **Streamlit App** - Interactive data science interface
- **FastAPI Backend** - RESTful API with automatic documentation

### Database & Storage
- **Supabase PostgreSQL** with vector extensions
- **Row Level Security (RLS)** for data protection
- **Real-time subscriptions** for live updates

## 🛠️ Quick Setup

### 1. Database Setup
Follow the comprehensive [Database Setup Guide](./DATABASE_SETUP_GUIDE.md) to:
- Create a new Supabase project
- Run the complete database migration
- Configure all environment variables

### 2. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd nextjs-lead-gen
npm install
```

**Streamlit:**
```bash
pip install -r requirements.txt
```

### 3. Start Applications

**Backend API:**
```bash
cd backend
python main.py
# Available at: http://localhost:8000
```

**Frontend Web App:**
```bash
cd nextjs-lead-gen
npm run dev
# Available at: http://localhost:3000
```

**Streamlit App:**
```bash
streamlit run main.py
# Available at: http://localhost:8501
```

## 📋 Required API Keys

- **OpenAI API Key** - For AI-powered features
- **Apify API Token** - For LinkedIn scraping
- **Google API Key & CSE ID** - For search functionality
- **Resend API Key** - For email delivery
- **Supabase Keys** - For database access

See [Database Setup Guide](./DATABASE_SETUP_GUIDE.md) for detailed configuration instructions.

## 🎯 Usage

1. **Configure ICP Criteria** - Define your ideal customer profile
2. **Generate Leads** - Use various scraping and search tools
3. **Score Leads** - AI automatically scores leads against your ICP
4. **Create Email Templates** - Build personalized email templates
5. **Run Campaigns** - Send targeted email campaigns
6. **Track Performance** - Monitor email engagement and lead quality

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Development

### Project Architecture
- **Backend**: FastAPI with async/await patterns
- **Frontend**: Next.js 14 with App Router
- **Database**: Supabase (PostgreSQL + Auth + Storage)
- **AI/ML**: OpenAI GPT-5-nano-2025-08-07 for scoring and email generation
- **Email**: Resend for transactional emails
- **Deployment**: Vercel (frontend) + Railway/Render (backend)

### Key Technologies
- Python 3.11+, FastAPI, Pydantic
- TypeScript, React 18, Next.js 14, Tailwind CSS
- PostgreSQL, pgvector, Supabase
- OpenAI API, LangChain
- Streamlit for data science workflows

## 📝 License

This project is proprietary. All rights reserved.