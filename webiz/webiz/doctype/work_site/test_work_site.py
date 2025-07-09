# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.utils import getdate, add_days


class TestWorkSite(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test customer if not exists
        if not frappe.db.exists("Customer", "Test Customer"):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Customer",
                "customer_type": "Company",
                "customer_group": "Commercial"
            })
            customer.insert(ignore_permissions=True)
    
    def test_work_site_creation(self):
        """Test basic work site creation"""
        work_site = frappe.get_doc({
            "doctype": "Work Site",
            "site_name": "Test Site 1",
            "customer": "Test Customer",
            "status": "Active",
            "address_line_1": "123 Test Street",
            "city": "Seoul",
            "country": "South Korea"
        })
        work_site.insert()
        
        self.assertEqual(work_site.site_name, "Test Site 1")
        self.assertEqual(work_site.status, "Active")
        self.assertIsNotNone(work_site.created_by)
        self.assertIsNotNone(work_site.created_date)
        
        # Clean up
        work_site.delete()
    
    def test_date_validation(self):
        """Test date validation"""
        work_site = frappe.get_doc({
            "doctype": "Work Site",
            "site_name": "Test Site 2",
            "customer": "Test Customer",
            "status": "Active",
            "address_line_1": "123 Test Street",
            "city": "Seoul",
            "country": "South Korea",
            "start_date": getdate(),
            "end_date": add_days(getdate(), -1)  # End date before start date
        })
        
        with self.assertRaises(frappe.ValidationError):
            work_site.insert()
    
    def test_coordinate_validation(self):
        """Test coordinate validation"""
        work_site = frappe.get_doc({
            "doctype": "Work Site",
            "site_name": "Test Site 3",
            "customer": "Test Customer",
            "status": "Active",
            "address_line_1": "123 Test Street",
            "city": "Seoul",
            "country": "South Korea",
            "latitude": 91.0  # Invalid latitude
        })
        
        with self.assertRaises(frappe.ValidationError):
            work_site.insert()
    
    def test_location_info(self):
        """Test location info formatting"""
        work_site = frappe.get_doc({
            "doctype": "Work Site",
            "site_name": "Test Site 4",
            "customer": "Test Customer",
            "status": "Active",
            "address_line_1": "123 Test Street",
            "address_line_2": "Suite 100",
            "city": "Seoul",
            "state": "Seoul",
            "postal_code": "12345",
            "country": "South Korea"
        })
        work_site.insert()
        
        location_info = work_site.get_location_info()
        expected = "123 Test Street, Suite 100, Seoul, Seoul, 12345, South Korea"
        self.assertEqual(location_info, expected)
        
        # Clean up
        work_site.delete()
    
    def tearDown(self):
        """Clean up test data"""
        # Remove test customer
        if frappe.db.exists("Customer", "Test Customer"):
            frappe.delete_doc("Customer", "Test Customer", ignore_permissions=True)
