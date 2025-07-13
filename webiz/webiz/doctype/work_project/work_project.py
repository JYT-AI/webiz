# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkProject(Document):
	def validate(self):
		"""Validate Work Project data"""
		self.validate_dates()
		self.validate_contract_amount()
	
	def validate_dates(self):
		"""Validate contract dates"""
		if self.contract_start_date and self.contract_end_date:
			if self.contract_start_date > self.contract_end_date:
				frappe.throw("계약 시작일은 종료일보다 이전이어야 합니다.")
	
	def validate_contract_amount(self):
		"""Validate contract amounts"""
		if self.monthly_contract_amount and self.monthly_contract_amount < 0:
			frappe.throw("월 계약금액은 0보다 커야 합니다.")
		
		if self.total_contract_amount and self.total_contract_amount < 0:
			frappe.throw("총 계약금액은 0보다 커야 합니다.")
	
	def before_save(self):
		"""Before save operations"""
		self.set_title()
	
	def set_title(self):
		"""Set title based on project and contract type"""
		if self.project_name and self.contract_type:
			self.title = f"{self.project_name} - {self.contract_type}"
		elif self.project_name:
			self.title = self.project_name
