# Test User Login Guide

## Test User Credentials

A test user has been created in the database with the following details:

- **User ID**: `c4b6d8f1-ad29-437d-90a3-016a0b4f5331`
- **Email**: `test@example.com`
- **Password**: `testpassword123`

## How to Login

1. **Start the Application**:
   - Make sure the Next.js development server is running: `npm run dev` in the `nextjs-lead-gen` directory
   - Open your browser and go to: http://localhost:3000

2. **Navigate to Login**:
   - Click on the "Login" button or go to: http://localhost:3000/login

3. **Enter Test User Credentials**:
   - Email: `test@example.com`
   - Password: `testpassword123`

4. **Access ICP Features**:
   - After logging in, navigate to the ICP page: http://localhost:3000/icp
   - You should see the ICP configuration interface with:
     - Scoring Criteria tab
     - Targeting Rules tab
     - Custom Prompt tab
     - Statistics tab (showing data for the 20 test leads)

## Test Data Available

The database now contains:
- **20 test leads** with realistic ICP scoring data
- **ICP scores** ranging from 0.1 to 9.8
- **ICP grades** distributed across A+, A, B+, B, C+, C, D+, D
- **Various industries**: Manufacturing, Healthcare, Technology, Finance, etc.
- **Different job titles**: Operations Manager, Plant Manager, Facility Manager, etc.

## Testing the ICP Functionality

1. **View Statistics**: Check the Statistics tab to see the distribution of your test leads
2. **Modify Scoring Criteria**: Adjust weights and enable/disable criteria
3. **Update Targeting Rules**: Change target industries, job titles, company sizes, and locations
4. **Generate Custom Prompts**: Use the AI prompt generator with your targeting criteria
5. **Save Settings**: Test the save functionality and verify changes persist

## Troubleshooting

- If you get authentication errors, make sure you're logged in with the test user
- If the ICP page shows no data, verify the test leads were inserted correctly
- Check the browser console for any JavaScript errors
- Ensure all environment variables are properly set in `.env.local`

## Database Access

The test user is associated with all 20 test leads through the `user_id` field, ensuring proper data isolation.