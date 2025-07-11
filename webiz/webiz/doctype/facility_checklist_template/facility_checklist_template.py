# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FacilityChecklistTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from webiz.webiz.doctype.facility_checklist_item.facility_checklist_item import FacilityChecklistItem

		approved_by: DF.Link | None
		checklist_items: DF.Table[FacilityChecklistItem]
		created_by: DF.Link | None
		description: DF.Text | None
		estimated_time: DF.Float | None
		facility_type: DF.Literal["Indoor", "Outdoor", "Mixed", "Specialized"]
		is_default: DF.Check
		last_used: DF.Datetime | None
		naming_series: DF.Literal["FCT-.YYYY.-"]
		priority: DF.Literal["Low", "Medium", "High", "Critical"]
		required_skills: DF.Text | None
		safety_requirements: DF.Text | None
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
		status: DF.Literal["Active", "Inactive", "Draft", "Archived"]
		template_name: DF.Data
		usage_count: DF.Int
	# end: auto-generated types

	def validate(self):
		"""Validate the checklist template."""
		self.validate_template_name()
		self.validate_checklist_items()
		self.validate_default_template()
		self.calculate_estimated_time()
		self.set_created_by()

	def validate_template_name(self):
		"""Validate template name uniqueness."""
		if self.template_name:
			existing = frappe.db.exists(
				"Facility Checklist Template",
				{
					"template_name": self.template_name,
					"name": ["!=", self.name]
				}
			)
			if existing:
				frappe.throw(_("Template name '{0}' already exists").format(self.template_name))

	def validate_checklist_items(self):
		"""Validate checklist items."""
		if not self.checklist_items:
			frappe.throw(_("At least one checklist item is required"))

		sequences = []
		for item in self.checklist_items:
			if item.item_sequence in sequences:
				frappe.throw(_("Duplicate sequence number: {0}").format(item.item_sequence))
			sequences.append(item.item_sequence)

		# Sort items by sequence
		self.checklist_items = sorted(self.checklist_items, key=lambda x: x.item_sequence)

	def validate_default_template(self):
		"""Ensure only one default template per facility type and site type."""
		if self.is_default:
			filters = {
				"facility_type": self.facility_type,
				"is_default": 1,
				"status": "Active",
				"name": ["!=", self.name]
			}
			
			if self.site_type:
				filters["site_type"] = self.site_type

			existing_default = frappe.db.exists("Facility Checklist Template", filters)
			if existing_default:
				frappe.throw(
					_("A default template already exists for {0} - {1}").format(
						self.facility_type, self.site_type or "All Site Types"
					)
				)

	def calculate_estimated_time(self):
		"""Calculate total estimated time from checklist items."""
		total_time = 0
		for item in self.checklist_items:
			if item.estimated_time:
				total_time += item.estimated_time

		# Convert minutes to hours
		self.estimated_time = total_time / 60 if total_time > 0 else 0

	def set_created_by(self):
		"""Set created by field."""
		if not self.created_by:
			self.created_by = frappe.session.user

	def before_save(self):
		"""Actions before saving."""
		self.calculate_estimated_time()

	def on_update(self):
		"""Actions after update."""
		self.update_usage_statistics()

	def update_usage_statistics(self):
		"""Update usage statistics."""
		if not self.usage_count:
			self.usage_count = 0

	@frappe.whitelist()
	def increment_usage(self):
		"""Increment usage count and update last used timestamp."""
		self.usage_count = (self.usage_count or 0) + 1
		self.last_used = frappe.utils.now()
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def get_checklist_config(self):
		"""Get complete checklist configuration for mobile/web app."""
		config = {
			"template_name": self.template_name,
			"description": self.description,
			"facility_type": self.facility_type,
			"site_type": self.site_type,
			"estimated_time": self.estimated_time,
			"required_skills": self.required_skills,
			"safety_requirements": self.safety_requirements,
			"special_instructions": self.special_instructions,
			"items": []
		}

		for item in sorted(self.checklist_items, key=lambda x: x.item_sequence):
			config["items"].append(item.get_item_config())

		return config

	@frappe.whitelist()
	def duplicate_template(self, new_name):
		"""Create a duplicate of this template with a new name."""
		new_template = frappe.copy_doc(self)
		new_template.template_name = new_name
		new_template.is_default = 0
		new_template.status = "Draft"
		new_template.usage_count = 0
		new_template.last_used = None
		new_template.created_by = frappe.session.user
		new_template.approved_by = None

		new_template.insert()
		return new_template


@frappe.whitelist()
def get_default_template(facility_type, site_type=None):
	"""Get default template for given facility and site type."""
	filters = {
		"facility_type": facility_type,
		"is_default": 1,
		"status": "Active"
	}
	
	if site_type:
		filters["site_type"] = site_type

	template = frappe.db.get_value(
		"Facility Checklist Template",
		filters,
		["name", "template_name"],
		as_dict=True
	)
	
	return template


@frappe.whitelist()
def get_templates_by_type(facility_type=None, site_type=None, status="Active"):
	"""Get templates filtered by facility type and site type."""
	filters = {"status": status}
	
	if facility_type:
		filters["facility_type"] = facility_type
	
	if site_type:
		filters["site_type"] = site_type

	templates = frappe.get_all(
		"Facility Checklist Template",
		filters=filters,
		fields=[
			"name", "template_name", "facility_type", "site_type",
			"estimated_time", "priority", "is_default", "usage_count"
		],
		order_by="is_default desc, usage_count desc, template_name"
	)
	
	return templates


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
	
	# Facility User can read and create
	if "Facility User" in frappe.get_roles(user) and ptype in ["read", "create", "write"]:
		return True
	
	return False


def get_permission_query_conditions(user):
	"""Get permission query conditions for list view."""
	if not user:
		user = frappe.session.user
	
	# System Manager and Facility Manager can see all
	if "System Manager" in frappe.get_roles(user) or "Facility Manager" in frappe.get_roles(user):
		return ""
	
	# Others can see active templates only
	return "`tabFacility Checklist Template`.status = 'Active'"
