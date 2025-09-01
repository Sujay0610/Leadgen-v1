// Debug script to test metrics API
const testMetricsAPI = async () => {
  try {
    console.log('Testing metrics API...');
    
    // Test the Next.js API route directly
    const response = await fetch('/api/leads/metrics?timeRange=30d', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    const data = await response.json();
    console.log('Response data:', data);
    
    if (data.status === 'success') {
      console.log('✅ API call successful');
      console.log('Metrics data:', data.metrics);
    } else {
      console.log('❌ API call failed:', data.message);
    }
    
  } catch (error) {
    console.error('❌ Error testing metrics API:', error);
  }
};

// Test authentication
const testAuth = async () => {
  try {
    const { createClient } = await import('@supabase/supabase-js');
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    );
    
    const { data: { session }, error } = await supabase.auth.getSession();
    
    if (error) {
      console.error('❌ Auth error:', error);
    } else if (session) {
      console.log('✅ User authenticated:', session.user.email);
      console.log('Access token exists:', !!session.access_token);
    } else {
      console.log('❌ No active session');
    }
  } catch (error) {
    console.error('❌ Error checking auth:', error);
  }
};

// Run tests
console.log('=== METRICS DEBUG SCRIPT ===');
testAuth();
testMetricsAPI();