#!/usr/bin/env python3
"""
CAD Finance & Business Suite - Backend API Testing
Tests all endpoints including auth, CRUD operations, and complex business logic.
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any

class CADFinanceAPITester:
    def __init__(self, base_url="https://wealthflow-18.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict = None, headers: Dict = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        
        # Default headers
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=req_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            details = f"Status: {response.status_code} (expected {expected_status})"
            if not success:
                details += f" | Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            return success, response_data

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        self.run_test("Root API Endpoint", "GET", "api/", 200)
        
        # Test health endpoint
        self.run_test("Health Check", "GET", "api/health", 200)

    def test_auth_flow(self):
        """Test complete authentication flow"""
        print("\n🔍 Testing Authentication Flow...")
        
        # Generate unique test user
        timestamp = int(datetime.now().timestamp())
        test_email = f"test.user.{timestamp}@example.com"
        test_password = "TestPassword123!"
        test_name = f"Test User {timestamp}"

        # Test registration
        success, response = self.run_test(
            "User Registration",
            "POST",
            "api/auth/register",
            200,
            data={
                "email": test_email,
                "password": test_password,
                "name": test_name
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user_id']
            print(f"    Registered user: {test_email}")
        else:
            print("    ❌ Registration failed, cannot continue auth tests")
            return False

        # Test login with same credentials
        success, response = self.run_test(
            "User Login",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": test_email,
                "password": test_password
            }
        )

        # Test get current user
        self.run_test("Get Current User", "GET", "api/auth/me", 200)
        
        return True

    def test_profile_management(self):
        """Test profile creation and management"""
        print("\n🔍 Testing Profile Management...")
        
        if not self.token:
            print("    ⚠️ Skipping profile tests - no auth token")
            return

        # Test profile creation
        profile_data = {
            "province": "Ontario",
            "home_sqft": 2000.0,
            "office_sqft": 200.0,
            "ev_purchase_price": 45000.0,
            "ev_purchase_date": "2026-01-01",
            "opening_ucc": 50000.0,
            "total_debt": 150000.0,
            "total_savings": 25000.0,
            "tfsa_balance": 15000.0,
            "rrsp_balance": 35000.0,
            "tfsa_goal": 7000.0,
            "rrsp_goal": 31560.0,
            "debt_goal": 100000.0
        }
        
        self.run_test(
            "Create Profile",
            "POST",
            "api/profile",
            200,
            data=profile_data
        )
        
        # Test get profile
        self.run_test("Get Profile", "GET", "api/profile", 200)
        
        # Test update profile
        updated_data = profile_data.copy()
        updated_data["total_savings"] = 30000.0
        
        self.run_test(
            "Update Profile",
            "PUT",
            "api/profile",
            200,
            data=updated_data
        )

    def test_dashboard_data(self):
        """Test dashboard data endpoint"""
        print("\n🔍 Testing Dashboard Data...")
        
        if not self.token:
            print("    ⚠️ Skipping dashboard tests - no auth token")
            return

        success, response = self.run_test("Get Dashboard Data", "GET", "api/dashboard", 200)
        
        if success:
            # Verify dashboard structure
            required_fields = [
                'net_worth', 'tax_liability', 'income_summary', 
                'goals', 'mileage', 'charging'
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test(
                    "Dashboard Structure",
                    False,
                    f"Missing fields: {missing_fields}"
                )
            else:
                self.log_test("Dashboard Structure", True, "All required fields present")

    def test_transaction_crud(self):
        """Test transaction CRUD operations"""
        print("\n🔍 Testing Transaction CRUD...")
        
        if not self.token:
            print("    ⚠️ Skipping transaction tests - no auth token")
            return

        # Create transaction
        transaction_data = {
            "date": "2026-01-15",
            "amount": 1500.0,
            "category": "Consulting",
            "type": "Income",
            "is_business": True,
            "business_use_percent": 100.0,
            "split_with_sister": False,
            "description": "Test consulting income"
        }
        
        success, response = self.run_test(
            "Create Transaction",
            "POST",
            "api/transactions",
            200,
            data=transaction_data
        )
        
        transaction_id = None
        if success and 'transaction' in response:
            transaction_id = response['transaction'].get('id')
        
        # Get transactions
        self.run_test("Get Transactions", "GET", "api/transactions", 200)
        
        # Delete transaction if created
        if transaction_id:
            self.run_test(
                "Delete Transaction",
                "DELETE",
                f"api/transactions/{transaction_id}",
                200
            )

    def test_mileage_crud(self):
        """Test mileage log CRUD operations"""
        print("\n🔍 Testing Mileage Log CRUD...")
        
        if not self.token:
            print("    ⚠️ Skipping mileage tests - no auth token")
            return

        # Create mileage log
        mileage_data = {
            "date": "2026-01-15",
            "start_km": 50000.0,
            "end_km": 50125.0,
            "purpose": "Business"
        }
        
        success, response = self.run_test(
            "Create Mileage Log",
            "POST",
            "api/mileage",
            200,
            data=mileage_data
        )
        
        log_id = None
        if success and 'log' in response:
            log_id = response['log'].get('id')
        
        # Get mileage logs
        self.run_test("Get Mileage Logs", "GET", "api/mileage", 200)
        
        # Delete log if created
        if log_id:
            self.run_test(
                "Delete Mileage Log",
                "DELETE",
                f"api/mileage/{log_id}",
                200
            )

    def test_charging_crud(self):
        """Test EV charging session CRUD operations"""
        print("\n🔍 Testing EV Charging CRUD...")
        
        if not self.token:
            print("    ⚠️ Skipping charging tests - no auth token")
            return

        # Create charging session
        charging_data = {
            "date": "2026-01-15",
            "kwh": 45.5,
            "cost": 18.20,
            "location": "Supercharger - Toronto"
        }
        
        success, response = self.run_test(
            "Create Charging Session",
            "POST",
            "api/charging",
            200,
            data=charging_data
        )
        
        session_id = None
        if success and 'session' in response:
            session_id = response['session'].get('id')
            # Verify rebate calculation
            expected_rebate = 45.5 * 0.03  # $0.03/kWh
            actual_rebate = response['session'].get('rebate_earned', 0)
            if abs(actual_rebate - expected_rebate) < 0.01:
                self.log_test("EV Rebate Calculation", True, f"Rebate: ${actual_rebate:.2f}")
            else:
                self.log_test("EV Rebate Calculation", False, f"Expected: ${expected_rebate:.2f}, Got: ${actual_rebate:.2f}")
        
        # Get charging sessions
        self.run_test("Get Charging Sessions", "GET", "api/charging", 200)
        
        # Delete session if created
        if session_id:
            self.run_test(
                "Delete Charging Session",
                "DELETE",
                f"api/charging/{session_id}",
                200
            )

    def test_sister_module(self):
        """Test sister module for bill splitting"""
        print("\n🔍 Testing Sister Module...")
        
        if not self.token:
            print("    ⚠️ Skipping sister module tests - no auth token")
            return

        # Create sister bill
        bill_data = {
            "date": "2026-01-15",
            "category": "Utilities",
            "amount": 200.0,
            "description": "Hydro bill"
        }
        
        success, response = self.run_test(
            "Create Sister Bill",
            "POST",
            "api/sister/bills",
            200,
            data=bill_data
        )
        
        bill_id = None
        if success and 'bill' in response:
            bill_id = response['bill'].get('id')
            # Verify split calculation
            expected_split = 200.0 / 2
            actual_split = response['bill'].get('split_amount', 0)
            if abs(actual_split - expected_split) < 0.01:
                self.log_test("Bill Split Calculation", True, f"Split: ${actual_split:.2f}")
            else:
                self.log_test("Bill Split Calculation", False, f"Expected: ${expected_split:.2f}, Got: ${actual_split:.2f}")
        
        # Get sister bills
        self.run_test("Get Sister Bills", "GET", "api/sister/bills", 200)
        
        # Test monthly summary
        self.run_test("Get Sister Summary", "GET", "api/sister/summary/2026-01", 200)
        
        # Delete bill if created
        if bill_id:
            self.run_test(
                "Delete Sister Bill",
                "DELETE",
                f"api/sister/bills/{bill_id}",
                200
            )

    def test_advanced_features(self):
        """Test advanced features like CSV export"""
        print("\n🔍 Testing Advanced Features...")
        
        if not self.token:
            print("    ⚠️ Skipping advanced tests - no auth token")
            return

        # Test CSV export
        try:
            url = f"{self.base_url}/api/export/csv"
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200 and 'text/csv' in response.headers.get('content-type', ''):
                self.log_test("CSV Export", True, "CSV file generated successfully")
            else:
                self.log_test("CSV Export", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("CSV Export", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting CAD Finance & Business Suite API Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run test suites
        self.test_health_endpoints()
        
        auth_success = self.test_auth_flow()
        if auth_success:
            self.test_profile_management()
            self.test_dashboard_data()
            self.test_transaction_crud()
            self.test_mileage_crud()
            self.test_charging_crud()
            self.test_sister_module()
            self.test_advanced_features()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            
            # Show failed tests
            failed_tests = [t for t in self.test_results if not t['success']]
            if failed_tests:
                print("\n🔍 Failed Tests:")
                for test in failed_tests:
                    print(f"  • {test['test']}: {test['details']}")
            
            return 1

    def get_test_summary(self):
        """Get test summary for reporting"""
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "test_results": self.test_results
        }

def main():
    tester = CADFinanceAPITester()
    exit_code = tester.run_all_tests()
    
    # Save detailed results
    summary = tester.get_test_summary()
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())