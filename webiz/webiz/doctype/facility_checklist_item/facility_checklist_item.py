# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FacilityChecklistItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		check_options: DF.Text | None
		description: DF.Text | None
		estimated_time: DF.Float | None
		expected_result: DF.Text | None
		is_mandatory: DF.Check
		item_sequence: DF.Int
		item_title: DF.Data
		item_type: DF.Literal["Check", "Measurement", "Photo", "Signature", "Text Input", "Multiple Choice"]
		tools_required: DF.Text | None
	# end: auto-generated types

	def validate(self):
		"""Validate the checklist item."""
		self.validate_sequence()
		self.validate_multiple_choice_options()

	def validate_sequence(self):
		"""Ensure sequence is positive."""
		if self.item_sequence <= 0:
			frappe.throw("Sequence must be a positive number")

	def validate_multiple_choice_options(self):
		"""Validate multiple choice options."""
		if self.item_type == "Multiple Choice":
			if not self.check_options:
				frappe.throw("Multiple Choice items must have options defined")
			
			# Validate that options are properly formatted
			options = self.get_options_list()
			if len(options) < 2:
				frappe.throw("Multiple Choice items must have at least 2 options")

	def get_options_list(self):
		"""Get list of options for multiple choice items."""
		if not self.check_options:
			return []
		
		options = [option.strip() for option in self.check_options.split('\n') if option.strip()]
		return options

	def get_item_config(self):
		"""Get configuration for this checklist item."""
		config = {
			"sequence": self.item_sequence,
			"title": self.item_title,
			"type": self.item_type,
			"mandatory": self.is_mandatory,
			"description": self.description,
			"expected_result": self.expected_result,
			"tools_required": self.tools_required,
			"estimated_time": self.estimated_time
		}
		
		if self.item_type == "Multiple Choice":
			config["options"] = self.get_options_list()
		
		return config
