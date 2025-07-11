# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class TimesheetChecklistResult(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checklist_item_title: DF.Data
		completed_time: DF.Datetime | None
		expected_result: DF.Text | None
		is_mandatory: DF.Check
		item_sequence: DF.Int
		item_type: DF.Literal["Check", "Measurement", "Photo", "Signature", "Text Input", "Multiple Choice"]
		result_notes: DF.Text | None
		result_photo: DF.Attach | None
		result_status: DF.Literal["미완료", "완료", "부분완료", "해당없음", "문제발생"]
		result_value: DF.Text | None
		template_item_reference: DF.Data | None
	# end: auto-generated types

	def validate(self):
		"""Validate the checklist result."""
		self.validate_mandatory_completion()
		self.validate_result_value()
		self.set_completion_time()

	def validate_mandatory_completion(self):
		"""Validate that mandatory items are completed."""
		if self.is_mandatory and self.result_status in ["미완료", "문제발생"]:
			frappe.msgprint(
				_("필수 항목 '{0}'이 완료되지 않았습니다.").format(self.checklist_item_title),
				indicator="orange"
			)

	def validate_result_value(self):
		"""Validate result value based on item type."""
		if self.item_type in ["Multiple Choice", "Text Input", "Measurement"]:
			if self.result_status == "완료" and not self.result_value:
				frappe.throw(
					_("'{0}' 항목의 결과 값을 입력해주세요.").format(self.checklist_item_title)
				)

		if self.item_type in ["Photo", "Signature"]:
			if self.result_status == "완료" and not self.result_photo:
				frappe.throw(
					_("'{0}' 항목의 첨부 파일을 업로드해주세요.").format(self.checklist_item_title)
				)

	def set_completion_time(self):
		"""Set completion time when status changes to completed."""
		if self.result_status == "완료" and not self.completed_time:
			self.completed_time = now()

	def get_result_summary(self):
		"""Get a summary of the result for reporting."""
		summary = {
			"sequence": self.item_sequence,
			"title": self.checklist_item_title,
			"type": self.item_type,
			"status": self.result_status,
			"mandatory": self.is_mandatory,
			"completed_time": self.completed_time
		}

		# Add result details based on type
		if self.item_type == "Check":
			summary["result"] = "완료" if self.result_status == "완료" else "미완료"
		elif self.item_type in ["Multiple Choice", "Text Input", "Measurement"]:
			summary["result"] = self.result_value or ""
		elif self.item_type in ["Photo", "Signature"]:
			summary["result"] = "첨부됨" if self.result_photo else "첨부 안됨"

		if self.result_notes:
			summary["notes"] = self.result_notes

		return summary

	def mark_completed(self, result_value=None, result_photo=None, notes=None):
		"""Mark this item as completed with optional result data."""
		self.result_status = "완료"
		self.completed_time = now()
		
		if result_value:
			self.result_value = result_value
		
		if result_photo:
			self.result_photo = result_photo
		
		if notes:
			self.result_notes = notes

	def mark_problem(self, notes=None):
		"""Mark this item as having a problem."""
		self.result_status = "문제발생"
		if notes:
			self.result_notes = notes

	@staticmethod
	def create_from_template_item(template_item):
		"""Create a checklist result from a template item."""
		return {
			"item_sequence": template_item.item_sequence,
			"checklist_item_title": template_item.item_title,
			"item_type": template_item.item_type,
			"is_mandatory": template_item.is_mandatory,
			"expected_result": template_item.expected_result,
			"template_item_reference": template_item.name,
			"result_status": "미완료"
		}

	def get_completion_percentage(self):
		"""Get completion percentage for this item."""
		if self.result_status == "완료":
			return 100
		elif self.result_status == "부분완료":
			return 50
		elif self.result_status == "해당없음":
			return 100  # Consider N/A as completed
		else:
			return 0

	def is_completed(self):
		"""Check if this item is completed."""
		return self.result_status in ["완료", "해당없음"]

	def has_problem(self):
		"""Check if this item has a problem."""
		return self.result_status == "문제발생"

	def get_display_result(self):
		"""Get formatted result for display."""
		if self.item_type == "Check":
			return "✅" if self.result_status == "완료" else "❌"
		elif self.item_type in ["Multiple Choice", "Text Input", "Measurement"]:
			return self.result_value or "-"
		elif self.item_type in ["Photo", "Signature"]:
			return "📎" if self.result_photo else "-"
		else:
			return self.result_status
