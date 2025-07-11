# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase


class TestFacilityChecklistTemplate(FrappeTestCase):
	def setUp(self):
		"""Set up test data."""
		# Clean up any existing test templates
		frappe.db.delete("Facility Checklist Template", {"template_name": ["like", "Test%"]})
		frappe.db.commit()

	def test_template_creation(self):
		"""Test basic template creation."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Office Cleaning",
			"facility_type": "Indoor",
			"site_type": "Office Building",
			"status": "Active",
			"description": "Standard office cleaning checklist",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Check vacuum cleaner",
					"item_type": "Check",
					"is_mandatory": 1,
					"description": "Ensure vacuum cleaner is working properly"
				},
				{
					"item_sequence": 2,
					"item_title": "Clean all desks",
					"item_type": "Check",
					"is_mandatory": 1,
					"estimated_time": 30
				}
			]
		})
		template.insert()
		
		self.assertEqual(template.template_name, "Test Office Cleaning")
		self.assertEqual(template.facility_type, "Indoor")
		self.assertEqual(len(template.checklist_items), 2)
		
		# Clean up
		template.delete()

	def test_estimated_time_calculation(self):
		"""Test automatic estimated time calculation."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Time Calculation",
			"facility_type": "Indoor",
			"status": "Active",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Task 1",
					"item_type": "Check",
					"estimated_time": 30  # 30 minutes
				},
				{
					"item_sequence": 2,
					"item_title": "Task 2",
					"item_type": "Check",
					"estimated_time": 60  # 60 minutes
				}
			]
		})
		template.insert()
		
		# Total should be 90 minutes = 1.5 hours
		self.assertEqual(template.estimated_time, 1.5)
		
		# Clean up
		template.delete()

	def test_default_template_validation(self):
		"""Test default template validation."""
		# Create first default template
		template1 = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Default 1",
			"facility_type": "Indoor",
			"site_type": "Office Building",
			"status": "Active",
			"is_default": 1,
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Test item",
					"item_type": "Check"
				}
			]
		})
		template1.insert()
		
		# Try to create second default template with same facility and site type
		template2 = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Default 2",
			"facility_type": "Indoor",
			"site_type": "Office Building",
			"status": "Active",
			"is_default": 1,
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Test item",
					"item_type": "Check"
				}
			]
		})
		
		# This should raise a validation error
		with self.assertRaises(frappe.ValidationError):
			template2.insert()
		
		# Clean up
		template1.delete()

	def test_sequence_validation(self):
		"""Test sequence number validation."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Sequence Validation",
			"facility_type": "Indoor",
			"status": "Active",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Task 1",
					"item_type": "Check"
				},
				{
					"item_sequence": 1,  # Duplicate sequence
					"item_title": "Task 2",
					"item_type": "Check"
				}
			]
		})
		
		# This should raise a validation error
		with self.assertRaises(frappe.ValidationError):
			template.insert()

	def test_multiple_choice_validation(self):
		"""Test multiple choice item validation."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Multiple Choice",
			"facility_type": "Indoor",
			"status": "Active",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Choose option",
					"item_type": "Multiple Choice",
					"check_options": "Option 1\nOption 2\nOption 3"
				}
			]
		})
		template.insert()
		
		# Test get_options_list method
		item = template.checklist_items[0]
		options = item.get_options_list()
		self.assertEqual(len(options), 3)
		self.assertIn("Option 1", options)
		
		# Clean up
		template.delete()

	def test_get_checklist_config(self):
		"""Test get_checklist_config method."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Config",
			"facility_type": "Indoor",
			"site_type": "Office Building",
			"status": "Active",
			"description": "Test description",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Test item",
					"item_type": "Check",
					"is_mandatory": 1,
					"description": "Test item description"
				}
			]
		})
		template.insert()
		
		config = template.get_checklist_config()
		
		self.assertEqual(config["template_name"], "Test Config")
		self.assertEqual(config["facility_type"], "Indoor")
		self.assertEqual(len(config["items"]), 1)
		self.assertEqual(config["items"][0]["title"], "Test item")
		
		# Clean up
		template.delete()

	def test_duplicate_template(self):
		"""Test template duplication."""
		original = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Original",
			"facility_type": "Indoor",
			"status": "Active",
			"is_default": 1,
			"usage_count": 5,
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Test item",
					"item_type": "Check"
				}
			]
		})
		original.insert()
		
		# Duplicate the template
		duplicate = original.duplicate_template("Test Duplicate")
		
		self.assertEqual(duplicate.template_name, "Test Duplicate")
		self.assertEqual(duplicate.is_default, 0)
		self.assertEqual(duplicate.status, "Draft")
		self.assertEqual(duplicate.usage_count, 0)
		self.assertEqual(len(duplicate.checklist_items), 1)
		
		# Clean up
		original.delete()
		duplicate.delete()

	def test_usage_increment(self):
		"""Test usage count increment."""
		template = frappe.get_doc({
			"doctype": "Facility Checklist Template",
			"naming_series": "FCT-.YYYY.-",
			"template_name": "Test Usage",
			"facility_type": "Indoor",
			"status": "Active",
			"checklist_items": [
				{
					"item_sequence": 1,
					"item_title": "Test item",
					"item_type": "Check"
				}
			]
		})
		template.insert()
		
		initial_count = template.usage_count or 0
		template.increment_usage()
		
		# Reload to get updated values
		template.reload()
		self.assertEqual(template.usage_count, initial_count + 1)
		self.assertIsNotNone(template.last_used)
		
		# Clean up
		template.delete()

	def tearDown(self):
		"""Clean up after tests."""
		# Clean up any remaining test data
		frappe.db.delete("Facility Checklist Template", {"template_name": ["like", "Test%"]})
		frappe.db.commit()
