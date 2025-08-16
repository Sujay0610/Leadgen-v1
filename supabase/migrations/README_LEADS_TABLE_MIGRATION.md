# Leads Table Migration Guide

## Issue Description

The application was encountering an error when inserting profile data:

```
Error inserting profile: {'message': "Could not find the 'about' column of 'leads' in the schema cache", 'code': 'PGRST204', 'hint': None, 'details': None}
```

This error occurred because the `leads` table schema was missing several columns that the application code was trying to insert, particularly the `about` field from LinkedIn profile enrichment.

## Root Cause Analysis

After analyzing the codebase, I found that:

1. **Apify LinkedIn Profile Scraper** (`enrich_profile_with_apify` function) extracts an `about` field from LinkedIn profiles
2. **Apollo.io Scraper** (`search_apollo_profiles` function) returns many additional fields not present in the original schema
3. **Field Mapping Function** (`map_profile_fields_to_db`) maps camelCase fields to snake_case database columns
4. **Original Schema** (20240601_create_leads_table.sql) was missing many fields that the application actually uses

## Complete Field Analysis

### Fields from Apify LinkedIn Enrichment:
- `about` - LinkedIn profile about/summary section ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `experience` - JSON string of work experiences ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `scraped_at` - Timestamp when profile was scraped ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `scraping_status` - Status of scraping (success, error, no_data) ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `error_message` - Error message if scraping failed ⚠️ **MISSING FROM ORIGINAL SCHEMA**

### Fields from Apollo.io Scraping:
- `email_address` - Primary email address ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `phone_number` - Phone number ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `departments` - Departments array ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `subdepartments` - Subdepartments array ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `functions` - Job functions array ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `work_experience_months` - Total work experience in months ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `employment_history` - JSON string of employment history ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `intent_strength` - Purchase intent strength ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `show_intent` - Whether to show intent data ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `email_domain_catchall` - Whether email domain accepts all emails ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `revealed_for_current_team` - Whether profile was revealed for current team ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `photo_url` - URL to profile photo ⚠️ **MISSING FROM ORIGINAL SCHEMA**
- `send_email_status` - Email sending status ⚠️ **MISSING FROM ORIGINAL SCHEMA**

## Migration Solutions

I've created two migration files to resolve this issue:

### Option 1: Update Existing Table (Recommended)
**File:** `20241201_update_leads_table.sql`

This migration:
- Adds all missing columns to the existing `leads` table
- Preserves existing data
- Adds appropriate indexes for performance
- Creates helpful views for common queries
- Adds column comments for documentation

**Usage:**
```sql
-- Run this migration to add missing columns
\i supabase/migrations/20241201_update_leads_table.sql
```

### Option 2: Recreate Table from Scratch
**File:** `20241201_create_complete_leads_table.sql`

This migration:
- Creates a completely new `leads` table with all required columns
- Includes all indexes, policies, and views
- Has an optional DROP statement (commented out by default)
- Includes automatic `updated_at` timestamp triggers
- Creates analytics views for ICP data

**Usage:**
```sql
-- If you want to recreate the table (WARNING: This will delete existing data)
-- Uncomment the DROP TABLE line in the migration file first
\i supabase/migrations/20241201_create_complete_leads_table.sql
```

## Field Mapping Reference

The application uses a field mapping function that converts camelCase fields to snake_case database columns:

```python
field_mapping = {
    'fullName': 'full_name',
    'firstName': 'first_name', 
    'lastName': 'last_name',
    'jobTitle': 'job_title',
    'companyName': 'company_name',
    'linkedinUrl': 'linkedin_url',
    'linkedin_url': 'linkedin_url',
    'emailAddress': 'email_address',
    'phoneNumber': 'phone_number',
    # ... and many more
}
```

## Recommended Action

1. **For Production:** Use Option 1 (update existing table) to preserve data
2. **For Development:** Use Option 2 (recreate table) for a clean schema

## Verification

After running the migration, verify the schema includes all required columns:

```sql
-- Check if all required columns exist
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'leads' 
ORDER BY ordinal_position;
```

## Performance Considerations

The migrations include indexes on commonly queried fields:
- `linkedin_url` (unique)
- `email` and `email_address`
- `icp_score`, `icp_percentage`, `icp_grade`
- `scraping_status`, `send_email_status`
- `created_at`, `scraped_at`
- Company and location fields

## Views Created

1. **`leads_summary`** - Common fields for general queries
2. **`leads_icp_analytics`** - ICP scoring analytics and email campaign stats

These views make it easier to query the most commonly used data without writing complex SELECT statements.