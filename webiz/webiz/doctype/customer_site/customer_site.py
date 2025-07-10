# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CustomerSite(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		access_requirements: DF.Text | None
		address_line1: DF.Data
		address_line2: DF.Data | None
		city: DF.Data
		contact_person: DF.Data | None
		contact_phone: DF.Data | None
		country: DF.Link
		customer: DF.Link
		customer_name: DF.Data | None
		email: DF.Data | None
		facility_type: DF.Literal["", "Indoor", "Outdoor", "Mixed"]
		floor_count: DF.Int | None
		naming_series: DF.Literal["SITE-.YYYY.-"]
		operating_hours: DF.Data | None
		phone: DF.Data | None
		pincode: DF.Data | None
		priority: DF.Literal["Low", "Medium", "High", "Critical"]
		safety_notes: DF.Text | None
		site_description: DF.Text | None
		site_name: DF.Data
		site_type: DF.Literal[
			"",
			"Office Building",
			"Factory",
			"Warehouse",
			"Retail Store",
			"Hospital",
			"School",
			"Hotel",
			"Residential",
			"Other",
		]
		special_instructions: DF.Text | None
		state: DF.Data | None
		status: DF.Literal["Active", "Inactive", "Under Maintenance", "Closed"]
		total_area: DF.Float | None
	# end: auto-generated types

	def validate(self):
		"""Validate the Customer Site document."""
		self.validate_customer()
		self.validate_contact_info()
		self.set_customer_name()

	def validate_customer(self):
		"""Validate that the customer exists and is active."""
		if self.customer:
			customer_doc = frappe.get_doc("Customer", self.customer)
			if customer_doc.disabled:
				frappe.throw(_("Customer {0} is disabled").format(self.customer))

	def validate_contact_info(self):
		"""Validate contact information."""
		if self.email and not frappe.utils.validate_email_address(self.email):
			frappe.throw(_("Please enter a valid email address"))

	def set_customer_name(self):
		"""Set customer name from customer link."""
		if self.customer and not self.customer_name:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

	def before_save(self):
		"""Actions to perform before saving the document."""
		self.set_customer_name()

	def get_full_address(self):
		"""Get formatted full address."""
		address_parts = [self.address_line1]
		
		if self.address_line2:
			address_parts.append(self.address_line2)
		
		address_parts.append(self.city)
		
		if self.state:
			address_parts.append(self.state)
		
		if self.pincode:
			address_parts.append(self.pincode)
		
		if self.country:
			country_name = frappe.db.get_value("Country", self.country, "country_name")
			if country_name:
				address_parts.append(country_name)
		
		return ", ".join(filter(None, address_parts))

	@frappe.whitelist()
	def get_site_summary(self):
		"""Get a summary of the site information."""
		return {
			"site_name": self.site_name,
			"customer": self.customer_name,
			"address": self.get_full_address(),
			"site_type": self.site_type,
			"status": self.status,
			"priority": self.priority,
			"total_area": self.total_area,
			"contact_person": self.contact_person,
			"contact_phone": self.contact_phone
		}


@frappe.whitelist()
def get_customer_sites(customer=None, status=None):
	"""Get customer sites with optional filters."""
	filters = {}
	
	if customer:
		filters["customer"] = customer
	
	if status:
		filters["status"] = status
	
	sites = frappe.get_all(
		"Customer Site",
		filters=filters,
		fields=[
			"name", "site_name", "customer", "customer_name", 
			"status", "site_type", "priority", "city", "state", "country"
		],
		order_by="creation desc"
	)
	
	return sites


def has_permission(doc, ptype, user):
	"""Check if user has permission to access the document."""
	if not doc:
		return True
	
	# System Manager has full access
	if "System Manager" in frappe.get_roles(user):
		return True
	
	# Facility Manager has full access
	if "Facility Manager" in frappe.get_roles(user):
		return True
	
	# Facility User has read access
	if "Facility User" in frappe.get_roles(user) and ptype == "read":
		return True
	
	return False


def get_permission_query_conditions(user):
	"""Get permission query conditions for list view."""
	if not user:
		user = frappe.session.user
	
	# System Manager and Facility Manager can see all
	if "System Manager" in frappe.get_roles(user) or "Facility Manager" in frappe.get_roles(user):
		return ""
	
	# Others can see active sites only
	return "`tabCustomer Site`.status = 'Active'"
