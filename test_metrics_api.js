// Test the metrics API directly
async function testMetricsAPI() {
  try {
    console.log('🔄 Testing metrics API...');
    
    // Test direct API call using fetch
    const response = await fetch('http://localhost:3000/api/leads/metrics', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('✅ API Response Status:', response.status);
    const data = await response.json();
    console.log('📊 API Response Data:', JSON.stringify(data, null, 2));
    
    if (data && data.metrics) {
      const metrics = data.metrics;
      console.log('\n📈 Metrics Summary:');
      console.log(`- Total Leads: ${metrics.totalLeads}`);
      console.log(`- Leads with Emails: ${metrics.leadsWithEmails}`);
      console.log(`- Average ICP Score: ${metrics.averageIcpScore}`);
      console.log(`- Recent Leads: ${metrics.recentLeads}`);
      console.log(`- High Quality Leads: ${metrics.highQualityLeads}`);
    }
    
  } catch (error) {
    console.error('❌ Error testing metrics API:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
  }
}

testMetricsAPI();