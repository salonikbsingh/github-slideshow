#!/usr/bin/env python3
import requests
import json

# Test tax projection with auth
base_url = 'https://wealthflow-18.preview.emergentagent.com'

# First register a user
auth_data = {
    'email': 'test.projection@example.com',
    'password': 'TestPass123!',
    'name': 'Test User'
}

try:
    # Register
    resp = requests.post(f'{base_url}/api/auth/register', json=auth_data, timeout=10)
    if resp.status_code == 200:
        token = resp.json()['token']
        print('✅ User registered successfully')
        
        # Test tax projection
        headers = {'Authorization': f'Bearer {token}'}
        projection_data = {'rrsp_contribution': 15000}
        
        resp = requests.post(f'{base_url}/api/tax/projection', json=projection_data, headers=headers, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            print('✅ Tax projection API working')
            print(f'Current bracket: {result["current"]["bracket"]}')
            print(f'Projected bracket: {result["projected"]["bracket"]}')
            print(f'Tax savings: ${result["savings"]["total"]:.2f}')
            print(f'Bracket dropped: {result["bracket_dropped"]}')
        else:
            print(f'❌ Tax projection failed: {resp.status_code} - {resp.text}')
    else:
        print(f'❌ Registration failed: {resp.status_code} - {resp.text}')
        
except Exception as e:
    print(f'❌ Error: {e}')