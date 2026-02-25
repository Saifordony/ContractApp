#!/usr/bin/env python3
"""
Contract Analysis Platform API Test Suite

This script comprehensively tests all API endpoints to ensure the application
is working correctly. It includes authentication, contract analysis, client
management, and system monitoring tests.

Usage:
    python test_api.py

Requirements:
    - requests
    - python-dotenv
    - PyMuPDF (for PDF creation)
"""

import requests
import json
import os
import time
import tempfile
from datetime import datetime
from typing import Dict, Optional, Any
from dotenv import load_dotenv
import io

# Try to import fitz for PDF creation, fallback to simple text if not available
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("PyMuPDF not available, will use text files instead of PDFs for testing")

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_USERNAME = "testuser_" + str(int(time.time()))
TEST_EMAIL = f"{TEST_USERNAME}@example.com"
TEST_PASSWORD = "testpassword123"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

class APITester:
    """Main test class for API endpoints"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.access_token = None
        self.client_id = None
        self.contract_id = None
        self.test_results = []
        self.session = requests.Session()
        
    def log_test(self, test_name: str, success: bool, message: str = "", response_data: Any = None):
        """Log test results"""
        status = f"{Colors.GREEN}✓ PASS{Colors.ENDC}" if success else f"{Colors.RED}✗ FAIL{Colors.ENDC}"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
        
        if not success and response_data:
            print(f"    Response: {response_data}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add authorization header if we have a token
        if self.access_token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.access_token:
            kwargs['headers']['Authorization'] = f"Bearer {self.access_token}"
            
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}Request failed: {e}{Colors.ENDC}")
            return None
    
    def create_sample_pdf(self) -> bytes:
        """Create a sample PDF for testing"""
        if not HAS_FITZ:
            # Return a dummy PDF-like content
            return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Create a simple PDF with contract content
        doc = fitz.open()
        page = doc.new_page()
        
        contract_text = """
        SAMPLE CONTRACT AGREEMENT
        
        This Agreement is entered into between Party A and Party B.
        
        TERMS AND CONDITIONS:
        
        1. SCOPE OF WORK
        Party A agrees to provide consulting services to Party B.
        
        2. PAYMENT TERMS
        Payment shall be made within 30 days of invoice date.
        Total amount: $10,000
        
        3. CONFIDENTIALITY
        Both parties agree to maintain confidentiality of all proprietary information.
        
        4. TERMINATION
        Either party may terminate this agreement with 30 days written notice.
        
        5. GOVERNING LAW
        This agreement shall be governed by the laws of [State/Country].
        
        6. LIMITATION OF LIABILITY
        In no event shall either party be liable for indirect damages.
        
        7. ENTIRE AGREEMENT
        This agreement constitutes the entire agreement between the parties.
        """
        
        page.insert_text((50, 50), contract_text, fontsize=12)
        pdf_bytes = doc.write()
        doc.close()
        
        return pdf_bytes
    
    def test_health_checks(self):
        """Test health check endpoints"""
        print(f"\n{Colors.BLUE}=== Testing Health Checks ==={Colors.ENDC}")
        
        # Test health check
        response = self.make_request("GET", "/healthz")
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("Health Check", True, f"Status: {data.get('status')}")
        else:
            self.log_test("Health Check", False, "Health check failed", response.json() if response else None)
        
        # Test readiness check
        response = self.make_request("GET", "/readyz")
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("Readiness Check", True, f"Status: {data.get('status')}")
        else:
            self.log_test("Readiness Check", False, "Readiness check failed", response.json() if response else None)
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print(f"\n{Colors.BLUE}=== Testing Authentication ==={Colors.ENDC}")
        
        # Test user registration
        register_data = {
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/register", json=register_data)
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("User Registration", True, f"User ID: {data.get('user_id')}")
        else:
            self.log_test("User Registration", False, "Registration failed", response.json() if response else None)
            return False
        
        # Test user login
        login_data = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", json=login_data)
        if response and response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            self.log_test("User Login", True, f"Token received: {self.access_token[:20]}...")
            return True
        else:
            self.log_test("User Login", False, "Login failed", response.json() if response else None)
            return False
    
    def test_client_management(self):
        """Test client management endpoints"""
        print(f"\n{Colors.BLUE}=== Testing Client Management ==={Colors.ENDC}")
        
        # Create a client
        client_data = {
            "name": "Test Client Company",
            "email": "client@example.com",
            "phone": "+1234567890"
        }
        
        response = self.make_request("POST", "/clients", json=client_data)
        if response and response.status_code == 200:
            data = response.json()
            self.client_id = data.get('client_id')
            self.log_test("Create Client", True, f"Client ID: {self.client_id}")
        else:
            self.log_test("Create Client", False, "Client creation failed", response.json() if response else None)
            return False
        
        # Get all clients
        response = self.make_request("GET", "/clients")
        if response and response.status_code == 200:
            data = response.json()
            clients = data.get('clients', [])
            self.log_test("Get All Clients", True, f"Found {len(clients)} clients")
        else:
            self.log_test("Get All Clients", False, "Get all clients failed", response.json() if response else None)
        
        # Get specific client
        response = self.make_request("GET", f"/clients/{self.client_id}")
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("Get Client by ID", True, f"Client name: {data.get('name')}")
        else:
            self.log_test("Get Client by ID", False, "Get client by ID failed", response.json() if response else None)
        
        # Update client
        update_data = {
            "name": "Updated Test Client Company",
            "email": "updated_client@example.com",
            "phone": "+0987654321"
        }
        
        response = self.make_request("PUT", f"/clients/{self.client_id}", json=update_data)
        if response and response.status_code == 200:
            self.log_test("Update Client", True, "Client updated successfully")
        else:
            self.log_test("Update Client", False, "Update client failed", response.json() if response else None)
        
        # Verify update by getting client again
        response = self.make_request("GET", f"/clients/{self.client_id}")
        if response and response.status_code == 200:
            data = response.json()
            if data.get('name') == "Updated Test Client Company":
                self.log_test("Verify Client Update", True, "Client update verified")
            else:
                self.log_test("Verify Client Update", False, "Client update not reflected")
        else:
            self.log_test("Verify Client Update", False, "Failed to verify client update", response.json() if response else None)
        
        return True
    
    def test_contract_management(self):
        """Test contract management endpoints"""
        print(f"\n{Colors.BLUE}=== Testing Contract Management ==={Colors.ENDC}")
        
        if not self.client_id:
            self.log_test("Contract Management", False, "No client ID available for testing")
            return False
        
        # Create a contract
        contract_data = {
            "title": "Test Contract Agreement",
            "client_id": self.client_id,
            "content": "This is a sample contract content for testing purposes.",
            "status": "pending"
        }
        
        response = self.make_request("POST", "/contracts", json=contract_data)
        if response and response.status_code == 200:
            data = response.json()
            self.contract_id = data.get('contract_id')
            self.log_test("Create Contract", True, f"Contract ID: {self.contract_id}")
        else:
            self.log_test("Create Contract", False, "Contract creation failed", response.json() if response else None)
            return False
        
        # Get all contracts
        response = self.make_request("GET", "/contracts")
        if response and response.status_code == 200:
            data = response.json()
            contracts = data.get('contracts', [])
            self.log_test("Get All Contracts", True, f"Found {len(contracts)} contracts")
        else:
            self.log_test("Get All Contracts", False, "Get all contracts failed", response.json() if response else None)
        
        # Get contract details
        response = self.make_request("GET", f"/contracts/{self.contract_id}")
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("Get Contract", True, f"Contract title: {data.get('title')}")
        else:
            self.log_test("Get Contract", False, "Get contract failed", response.json() if response else None)
        
        # Update contract
        update_data = {
            "title": "Updated Test Contract Agreement",
            "client_id": self.client_id,
            "content": "Updated contract content for testing purposes.",
            "status": "reviewed"
        }
        
        response = self.make_request("PUT", f"/contracts/{self.contract_id}", json=update_data)
        if response and response.status_code == 200:
            self.log_test("Update Contract", True, "Contract updated successfully")
        else:
            self.log_test("Update Contract", False, "Update contract failed", response.json() if response else None)
        
        # Get client contracts
        response = self.make_request("GET", f"/clients/{self.client_id}/contracts")
        if response and response.status_code == 200:
            data = response.json()
            contracts = data.get('contracts', [])
            self.log_test("Get Client Contracts", True, f"Found {len(contracts)} contracts")
        else:
            self.log_test("Get Client Contracts", False, "Get client contracts failed", response.json() if response else None)
        
        return True
    
    def test_genai_analysis(self):
        """Test GenAI contract analysis endpoints"""
        print(f"\n{Colors.BLUE}=== Testing GenAI Contract Analysis ==={Colors.ENDC}")
        
        # Create sample PDF
        pdf_bytes = self.create_sample_pdf()
        
        # Test contract analysis
        files = {
            'file': ('test_contract.pdf', pdf_bytes, 'application/pdf')
        }
        
        response = self.make_request("POST", "/genai/analyze-contract", files=files)
        if response and response.status_code == 200:
            data = response.json()
            clauses = data.get('clauses', {})
            self.log_test("Contract Analysis", True, f"Extracted {len(clauses)} clauses")
            
            # Test contract evaluation with the extracted clauses
            if clauses:
                eval_response = self.make_request("POST", "/genai/evaluate-contract", json=clauses)
                if eval_response and eval_response.status_code == 200:
                    eval_data = eval_response.json()
                    approved = eval_data.get('approved', False)
                    self.log_test("Contract Evaluation", True, f"Approved: {approved}")
                else:
                    self.log_test("Contract Evaluation", False, "Evaluation failed", eval_response.json() if eval_response else None)
            
        else:
            self.log_test("Contract Analysis", False, "Analysis failed", response.json() if response else None)
        
        # Test complete analysis pipeline
        if self.contract_id:
            response = self.make_request("POST", f"/contracts/{self.contract_id}/init-genai")
            if response and response.status_code == 200:
                data = response.json()
                self.log_test("Complete Analysis Pipeline", True, f"Analysis ID: {data.get('analysis_id')}")
            else:
                self.log_test("Complete Analysis Pipeline", False, "Pipeline failed", response.json() if response else None)
    
    def test_system_monitoring(self):
        """Test system monitoring endpoints"""
        print(f"\n{Colors.BLUE}=== Testing System Monitoring ==={Colors.ENDC}")
        
        # Test metrics endpoint
        response = self.make_request("GET", "/metrics")
        if response and response.status_code == 200:
            data = response.json()
            total_requests = data.get('total_requests', 0)
            self.log_test("System Metrics", True, f"Total requests: {total_requests}")
        else:
            self.log_test("System Metrics", False, "Metrics failed", response.json() if response else None)
        
        # Test logs endpoint
        response = self.make_request("GET", "/logs?limit=5")
        if response and response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            self.log_test("System Logs", True, f"Retrieved {len(logs)} logs")
        else:
            self.log_test("System Logs", False, "Logs failed", response.json() if response else None)
        
        # Test logs with filters
        response = self.make_request("GET", f"/logs?user={TEST_USERNAME}&status=success")
        if response and response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            self.log_test("Filtered Logs", True, f"Retrieved {len(logs)} filtered logs")
        else:
            self.log_test("Filtered Logs", False, "Filtered logs failed", response.json() if response else None)    
    
    def test_cleanup(self):
        """Clean up test data"""
        print(f"\n{Colors.BLUE}=== Cleaning Up Test Data ==={Colors.ENDC}")
        
        # Delete test contract
        if self.contract_id:
            response = self.make_request("DELETE", f"/contracts/{self.contract_id}")
            if response and response.status_code == 200:
                self.log_test("Delete Contract", True, "Contract deleted successfully")
            else:
                self.log_test("Delete Contract", False, "Delete contract failed", response.json() if response else None)
        
        # Delete test client
        if self.client_id:
            response = self.make_request("DELETE", f"/clients/{self.client_id}")
            if response and response.status_code == 200:
                self.log_test("Delete Client", True, "Client deleted successfully")
            else:
                self.log_test("Delete Client", False, "Delete client failed", response.json() if response else None)
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"{Colors.BOLD}{Colors.MAGENTA}Starting API Test Suite{Colors.ENDC}")
        print(f"{Colors.CYAN}Testing API at: {self.base_url}{Colors.ENDC}")
        print(f"{Colors.CYAN}Test user: {TEST_USERNAME}{Colors.ENDC}")
        
        start_time = time.time()
        
        # Run tests in order
        self.test_health_checks()
        
        if self.test_authentication():
            self.test_client_management()
            self.test_contract_management()
            self.test_genai_analysis()
            self.test_system_monitoring()
            self.test_cleanup()
        else:
            print(f"{Colors.RED}Authentication failed, skipping remaining tests{Colors.ENDC}")
        
        # Print summary
        self.print_summary(start_time)
    
    def print_summary(self, start_time: float):
        """Print test summary"""
        end_time = time.time()
        duration = end_time - start_time
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}Test Summary{Colors.ENDC}")
        print(f"Total tests: {total_tests}")
        print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.ENDC}")
        print(f"{Colors.RED}Failed: {failed_tests}{Colors.ENDC}")
        print(f"Duration: {duration:.2f} seconds")
        
        if failed_tests > 0:
            print(f"\n{Colors.RED}Failed tests:{Colors.ENDC}")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(f"\n{Colors.BOLD}Success rate: {success_rate:.1f}%{Colors.ENDC}")
        
        if success_rate >= 80:
            print(f"{Colors.GREEN}API is working well!{Colors.ENDC}")
        elif success_rate >= 60:
            print(f"{Colors.YELLOW}API has some issues but is mostly functional{Colors.ENDC}")
        else:
            print(f"{Colors.RED}API has significant issues{Colors.ENDC}")
    
    def save_results(self, filename: str = "test_results.json"):
        """Save test results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                'test_results': self.test_results,
                'summary': {
                    'total_tests': len(self.test_results),
                    'passed_tests': sum(1 for r in self.test_results if r['success']),
                    'failed_tests': sum(1 for r in self.test_results if not r['success']),
                    'success_rate': (sum(1 for r in self.test_results if r['success']) / len(self.test_results)) * 100 if self.test_results else 0
                }
            }, f, indent=2)
        print(f"Test results saved to {filename}")

def main():
    """Main function"""
    print(f"{Colors.BOLD}Contract Analysis Platform API Tester{Colors.ENDC}")
    print(f"Testing API at: {API_BASE_URL}")
    
    # Check if API is reachable
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=10)
        if response.status_code != 200:
            print(f"{Colors.RED}API is not reachable or not healthy{Colors.ENDC}")
            print(f"Make sure the API is running at {API_BASE_URL}")
            return
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Cannot connect to API: {e}{Colors.ENDC}")
        print(f"Make sure the API is running at {API_BASE_URL}")
        return
    
    # Run tests
    tester = APITester()
    tester.run_all_tests()
    
    # Save results
    tester.save_results()

if __name__ == "__main__":
    main()