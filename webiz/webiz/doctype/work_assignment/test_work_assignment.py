# Copyright (c) 2025, WeBiz and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import today, add_days


class TestWorkAssignment(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test customer if not exists
        if not frappe.db.exists("Customer", "Test Customer"):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Customer",
                "customer_type": "Company"
            })
            customer.insert()
            
        # Create test employee if not exists
        if not frappe.db.exists("Employee", "EMP-TEST-001"):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee": "EMP-TEST-001",
                "employee_name": "Test Employee",
                "status": "Active"
            })
            employee.insert()
            
        # Create test work site if not exists
        if not frappe.db.exists("Work Site", "Test Site"):
            work_site = frappe.get_doc({
                "doctype": "Work Site",
                "naming_series": "WS-.YYYY.-",
                "site_name": "Test Site",
                "customer": "Test Customer",
                "address": "Test Address",
                "status": "Active"
            })
            work_site.insert()
            
        # Create test work template if not exists
        if not frappe.db.exists("Work Template", "Test Template"):
            work_template = frappe.get_doc({
                "doctype": "Work Template",
                "naming_series": "WT-.YYYY.-",
                "template_name": "Test Template",
                "category": "청소",
                "status": "Active",
                "estimated_minutes": 60
            })
            work_template.insert()
            
        # Create test work task if not exists
        if not frappe.db.exists("Work Task", "Test Task"):
            work_task = frappe.get_doc({
                "doctype": "Work Task",
                "naming_series": "WT-.YYYY.-",
                "task_name": "Test Task",
                "work_location": "Test Site",
                "checklist_template": "Test Template",
                "estimated_duration": 60,
                "priority": "Medium",
                "status": "Active",
                "effective_from": today()
            })
            work_task.insert()
            
    def test_work_assignment_creation(self):
        """Test basic work assignment creation"""
        work_assignment = frappe.get_doc({
            "doctype": "Work Assignment",
            "naming_series": "WA-.YYYY.-",
            "work_task": "Test Task",
            "assigned_to": "EMP-TEST-001",
            "assignment_date": today(),
            "start_date": today(),
            "assignment_status": "Assigned"
        })
        
        # Should not raise any exception
        work_assignment.insert()
        self.assertTrue(work_assignment.name)
        self.assertTrue(work_assignment.assignment_name)
        self.assertEqual(work_assignment.created_by, frappe.session.user)
        
        # Clean up
        work_assignment.delete()
        
    def test_date_validation(self):
        """Test date validation"""
        work_assignment = frappe.get_doc({
            "doctype": "Work Assignment",
            "naming_series": "WA-.YYYY.-",
            "work_task": "Test Task",
            "assigned_to": "EMP-TEST-001",
            "assignment_date": today(),
            "start_date": today(),
            "end_date": add_days(today(), -1),  # End date before start date
            "assignment_status": "Assigned"
        })
        
        # Should raise validation error
        with self.assertRaises(frappe.ValidationError):
            work_assignment.insert()
            
    def tearDown(self):
        """Clean up test data"""
        # Clean up any test documents
        frappe.db.rollback()
