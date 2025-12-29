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
    def __init__(self, base_url="https://finance-suite-10.preview.emergentagent.com"):
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
        
        # Use the test credentials from the review request
        test_email = "test@test.com"
        test_password = "testpass123"

        # Test login with provided credentials
        success, response = self.run_test(
            "User Login (Test Credentials)",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": test_email,
                "password": test_password
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user_id']
            print(f"    Logged in user: {test_email}")
        else:
            print("    ❌ Login failed with test credentials, cannot continue tests")
            return False

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

    def test_2026_ontario_tax_implementation(self):
        """Test specific 2026 Ontario tax implementation features"""
        print("\n🔍 Testing 2026 Ontario Tax Implementation...")
        
        if not self.token:
            print("    ⚠️ Skipping Ontario tax tests - no auth token")
            return

        # Test 1: Dashboard Tax Breakdown - Verify all 6 components
        print("    Testing Dashboard Tax Breakdown...")
        success, response = self.run_test("Dashboard Tax Breakdown", "GET", "api/dashboard", 200)
        
        if success and 'tax_liability' in response:
            tax_data = response['tax_liability']
            required_components = ['federal', 'ontario', 'ontario_health_premium', 'cpp', 'cpp2', 'ei', 'ei_opted_in']
            missing_components = [comp for comp in required_components if comp not in tax_data]
            
            if missing_components:
                self.log_test("Dashboard Tax Components", False, f"Missing: {missing_components}")
            else:
                self.log_test("Dashboard Tax Components", True, "All 6 tax components present")
                
                # Verify EI opt-in status for test user (should be True)
                ei_opted_in = tax_data.get('ei_opted_in', False)
                if ei_opted_in:
                    self.log_test("EI Opt-in Status", True, f"EI opted in: {ei_opted_in}")
                    # Verify EI amount is calculated (should be > 0)
                    ei_amount = tax_data.get('ei', 0)
                    if ei_amount > 0:
                        self.log_test("EI Premium Calculation", True, f"EI Premium: ${ei_amount:.2f}")
                    else:
                        self.log_test("EI Premium Calculation", False, "EI amount is 0 despite opt-in")
                else:
                    self.log_test("EI Opt-in Status", False, "Test user should have EI opted in")
                
                # Verify Ontario Health Premium is calculated
                ohp_amount = tax_data.get('ontario_health_premium', 0)
                if ohp_amount > 0:
                    self.log_test("Ontario Health Premium", True, f"OHP: ${ohp_amount:.2f}")
                else:
                    self.log_test("Ontario Health Premium", False, "OHP amount is 0")

        # Test 2: Profile with Contribution Room
        print("    Testing Profile Contribution Room...")
        
        # First get current profile
        success, current_profile = self.run_test("Get Current Profile", "GET", "api/profile", 200)
        
        if success:
            # Update profile with contribution room values
            profile_data = current_profile.copy() if current_profile else {}
            profile_data.update({
                "tfsa_contribution_room": 95000.0,  # Test value
                "rrsp_contribution_room": 85000.0,  # Test value from review request
                "ei_opt_in": True  # Ensure EI is opted in
            })
            
            success, response = self.run_test(
                "Update Profile with Contribution Room",
                "PUT",
                "api/profile",
                200,
                data=profile_data
            )
            
            if success:
                # Verify the values were saved by getting profile again
                success, updated_profile = self.run_test("Verify Profile Update", "GET", "api/profile", 200)
                
                if success:
                    tfsa_room = updated_profile.get('tfsa_contribution_room', 0)
                    rrsp_room = updated_profile.get('rrsp_contribution_room', 0)
                    ei_opt_in = updated_profile.get('ei_opt_in', False)
                    
                    if tfsa_room == 95000.0:
                        self.log_test("TFSA Contribution Room Save", True, f"TFSA Room: ${tfsa_room:,.0f}")
                    else:
                        self.log_test("TFSA Contribution Room Save", False, f"Expected $95,000, got ${tfsa_room:,.0f}")
                    
                    if rrsp_room == 85000.0:
                        self.log_test("RRSP Contribution Room Save", True, f"RRSP Room: ${rrsp_room:,.0f}")
                    else:
                        self.log_test("RRSP Contribution Room Save", False, f"Expected $85,000, got ${rrsp_room:,.0f}")
                    
                    if ei_opt_in:
                        self.log_test("EI Opt-in Save", True, "EI opt-in saved correctly")
                    else:
                        self.log_test("EI Opt-in Save", False, "EI opt-in not saved")

        # Test 3: Tax Projection with User's RRSP Room
        print("    Testing Tax Projection with User's RRSP Room...")
        
        projection_data = {"rrsp_contribution": 20000}
        success, response = self.run_test(
            "Tax Projection with RRSP",
            "POST",
            "api/tax/projection",
            200,
            data=projection_data
        )
        
        if success:
            # Verify user's actual RRSP room is returned (85000, not default 31560)
            rrsp_room = response.get('rrsp_contribution_room', 0)
            if rrsp_room == 85000:
                self.log_test("Tax Projection RRSP Room", True, f"User's RRSP Room: ${rrsp_room:,.0f}")
            else:
                self.log_test("Tax Projection RRSP Room", False, f"Expected $85,000, got ${rrsp_room:,.0f}")
            
            # Verify OHP appears in current and projected sections
            current_ohp = response.get('current', {}).get('ontario_health_premium', 0)
            projected_ohp = response.get('projected', {}).get('ontario_health_premium', 0)
            
            if current_ohp > 0:
                self.log_test("Tax Projection Current OHP", True, f"Current OHP: ${current_ohp:.2f}")
            else:
                self.log_test("Tax Projection Current OHP", False, "Current OHP is 0")
            
            if 'projected' in response and 'ontario_health_premium' in response['projected']:
                self.log_test("Tax Projection Projected OHP", True, f"Projected OHP: ${projected_ohp:.2f}")
            else:
                self.log_test("Tax Projection Projected OHP", False, "Projected OHP missing")
            
            # Verify OHP savings calculation
            ohp_savings = response.get('savings', {}).get('ohp', 0)
            if 'ohp' in response.get('savings', {}):
                self.log_test("Tax Projection OHP Savings", True, f"OHP Savings: ${ohp_savings:.2f}")
            else:
                self.log_test("Tax Projection OHP Savings", False, "OHP savings not calculated")

        # Test 4: EI Opt-in Toggle Effect
        print("    Testing EI Opt-in Toggle Effect...")
        
        # First, ensure EI is opted in and get current dashboard
        profile_data = {"ei_opt_in": True}
        success, response = self.run_test(
            "Set EI Opt-in True",
            "PUT",
            "api/profile",
            200,
            data=profile_data
        )
        
        if success:
            # Get dashboard with EI opted in
            success, dashboard_ei_on = self.run_test("Dashboard with EI On", "GET", "api/dashboard", 200)
            
            if success:
                ei_amount_on = dashboard_ei_on.get('tax_liability', {}).get('ei', 0)
                
                # Now toggle EI off
                profile_data = {"ei_opt_in": False}
                success, response = self.run_test(
                    "Set EI Opt-in False",
                    "PUT",
                    "api/profile",
                    200,
                    data=profile_data
                )
                
                if success:
                    # Get dashboard with EI opted out
                    success, dashboard_ei_off = self.run_test("Dashboard with EI Off", "GET", "api/dashboard", 200)
                    
                    if success:
                        ei_amount_off = dashboard_ei_off.get('tax_liability', {}).get('ei', 0)
                        
                        # Verify EI changes from positive amount to 0
                        if ei_amount_on > 0 and ei_amount_off == 0:
                            self.log_test("EI Toggle Effect", True, f"EI: ${ei_amount_on:.2f} → ${ei_amount_off:.2f}")
                        else:
                            self.log_test("EI Toggle Effect", False, f"Expected EI to change from >0 to 0, got {ei_amount_on:.2f} → {ei_amount_off:.2f}")
                
                # Reset EI to opted in for other tests
                profile_data = {"ei_opt_in": True}
                self.run_test("Reset EI Opt-in True", "PUT", "api/profile", 200, data=profile_data)

    def test_totp_backup_codes(self):
        """Test TOTP setup returns backup codes"""
        print("\n🔍 Testing TOTP Backup Codes...")
        
        if not self.token:
            print("    ⚠️ Skipping TOTP tests - no auth token")
            return

        success, response = self.run_test("TOTP Setup", "POST", "api/auth/totp/setup", 200)
        
        if success:
            # Verify backup codes are returned
            if 'backup_codes' in response and isinstance(response['backup_codes'], list):
                backup_count = len(response['backup_codes'])
                if backup_count == 10:
                    self.log_test("TOTP Backup Codes", True, f"Generated {backup_count} backup codes")
                else:
                    self.log_test("TOTP Backup Codes", False, f"Expected 10 codes, got {backup_count}")
            else:
                self.log_test("TOTP Backup Codes", False, "No backup_codes array in response")

    def test_grizzle_rebate_logic(self):
        """Test Grizzl-E rebate logic in charging and dashboard"""
        print("\n🔍 Testing Grizzl-E Rebate Logic...")
        
        if not self.token:
            print("    ⚠️ Skipping Grizzl-E tests - no auth token")
            return

        # Create charging session to test rebate
        charging_data = {
            "date": "2026-01-15",
            "kwh": 100.0,  # 100 kWh for easy calculation
            "cost": 40.00,
            "location": "Test Location"
        }
        
        success, response = self.run_test(
            "Create Charging Session (Grizzl-E)",
            "POST",
            "api/charging",
            200,
            data=charging_data
        )
        
        session_id = None
        if success and 'session' in response:
            session_id = response['session'].get('id')
            # Verify Grizzl-E rebate calculation ($0.03/kWh)
            expected_rebate = 100.0 * 0.03  # $3.00
            actual_rebate = response['session'].get('rebate_earned', 0)
            if abs(actual_rebate - expected_rebate) < 0.01:
                self.log_test("Grizzl-E Rebate Calculation", True, f"Rebate: ${actual_rebate:.2f}")
            else:
                self.log_test("Grizzl-E Rebate Calculation", False, f"Expected: ${expected_rebate:.2f}, Got: ${actual_rebate:.2f}")
        
        # Test dashboard shows Grizzl-E rebate
        success, dashboard_response = self.run_test("Dashboard Grizzl-E Data", "GET", "api/dashboard", 200)
        
        if success and 'charging' in dashboard_response:
            charging_data = dashboard_response['charging']
            if 'grizzle_rebate' in charging_data:
                self.log_test("Dashboard Grizzl-E Rebate", True, f"Rebate shown: ${charging_data['grizzle_rebate']:.2f}")
            else:
                self.log_test("Dashboard Grizzl-E Rebate", False, "grizzle_rebate field missing from dashboard")
        
        # Clean up
        if session_id:
            self.run_test(
                "Delete Test Charging Session",
                "DELETE",
                f"api/charging/{session_id}",
                200
            )

    def test_sister_pdf_grizzle_credit(self):
        """Test Sister PDF includes Grizzl-E Energy Credit section"""
        print("\n🔍 Testing Sister PDF Grizzl-E Credit...")
        
        if not self.token:
            print("    ⚠️ Skipping Sister PDF tests - no auth token")
            return

        # Create a charging session first
        charging_data = {
            "date": "2026-01-15",
            "kwh": 50.0,
            "cost": 20.00,
            "location": "Test Location"
        }
        
        success, response = self.run_test(
            "Create Charging for PDF Test",
            "POST",
            "api/charging",
            200,
            data=charging_data
        )
        
        session_id = None
        if success and 'session' in response:
            session_id = response['session'].get('id')
        
        # Test PDF generation
        try:
            url = f"{self.base_url}/api/sister/pdf/2026-01"
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                self.log_test("Sister PDF Generation", True, "PDF generated successfully")
                # Note: We can't easily verify PDF content without additional libraries
                # but the fact that it generates without error is a good sign
            else:
                self.log_test("Sister PDF Generation", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sister PDF Generation", False, f"Error: {str(e)}")
        
        # Clean up
        if session_id:
            self.run_test(
                "Delete PDF Test Charging Session",
                "DELETE",
                f"api/charging/{session_id}",
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
        
        # Test new 2026 features first
        self.test_2026_tax_features()
        
        auth_success = self.test_auth_flow()
        if auth_success:
            self.test_profile_management()
            self.test_dashboard_data()
            self.test_transaction_crud()
            self.test_mileage_crud()
            self.test_charging_crud()
            self.test_sister_module()
            self.test_advanced_features()
            
            # Test new authenticated features
            self.test_totp_backup_codes()
            self.test_grizzle_rebate_logic()
            self.test_sister_pdf_grizzle_credit()
        
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