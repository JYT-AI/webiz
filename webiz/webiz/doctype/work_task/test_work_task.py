# Copyright (c) 2025, WeBiz and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import today, add_days


class TestWorkTask(unittest.TestCase):
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
            
    def test_work_task_creation(self):
        """Test basic work task creation"""
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
        
        # Should not raise any exception
        work_task.insert()
        self.assertTrue(work_task.name)
        self.assertEqual(work_task.created_by, frappe.session.user)
        
        # Clean up
        work_task.delete()
        
    def test_date_validation(self):
        """Test date validation"""
        work_task = frappe.get_doc({
            "doctype": "Work Task",
            "naming_series": "WT-.YYYY.-",
            "task_name": "Test Task with Invalid Dates",
            "work_location": "Test Site",
            "checklist_template": "Test Template",
            "estimated_duration": 60,
            "priority": "Medium",
            "status": "Active",
            "effective_from": today(),
            "effective_to": add_days(today(), -1)  # End date before start date
        })
        
        # Should raise validation error
        with self.assertRaises(frappe.ValidationError):
            work_task.insert()
            
    def tearDown(self):
        """Clean up test data"""
        # Clean up any test documents
        frappe.db.rollback()
