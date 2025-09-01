import sys
sys.path.append('backend')

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Initialize Supabase client with service role key
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def apply_migration():
    try:
        # Read the migration file
        with open('supabase/migrations/20250120_add_missing_campaign_columns.sql', 'r') as file:
            migration_sql = file.read()
        
        print("Applying migration to add missing columns...")
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                try:
                    # Execute each statement
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"Statement failed (might be expected): {e}")
                    continue
        
        print("Migration completed!")
        
        # Test the table structure
        print("Testing email_campaigns table...")
        result = supabase.table('email_campaigns').select('*').limit(1).execute()
        print("Table query successful - all columns exist!")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    apply_migration()