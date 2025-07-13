# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import calendar


class WorkTask(Document):
	def validate(self):
		"""Validate Work Task data"""
		self.validate_dates()
		self.validate_template_settings()
	
	def validate_dates(self):
		"""Validate repeat dates"""
		if self.repeat_start_date and self.repeat_end_date:
			if self.repeat_start_date > self.repeat_end_date:
				frappe.throw("반복 시작일은 종료일보다 이전이어야 합니다.")
	
	def validate_template_settings(self):
		"""Validate template settings"""
		if self.is_template and self.auto_repeat_enabled:
			if not self.repeat_start_date:
				frappe.throw("자동 반복이 활성화된 경우 반복 시작일이 필요합니다.")
			if not self.repeat_frequency:
				frappe.throw("자동 반복이 활성화된 경우 반복 주기가 필요합니다.")
	
	def before_save(self):
		"""Before save operations"""
		self.set_title()
		if self.is_template and self.auto_repeat_enabled:
			self.set_next_execution_date()
	
	def set_title(self):
		"""Set title based on work project and customer site"""
		if self.work_project and self.customer_site:
			work_project_doc = frappe.get_doc("Work Project", self.work_project)
			site_doc = frappe.get_doc("Customer Site", self.customer_site)
			self.title = f"{work_project_doc.title} - {site_doc.site_name}"
		elif self.subject:
			self.title = self.subject
	
	def set_next_execution_date(self):
		"""Set next execution date based on repeat settings"""
		if not self.repeat_start_date:
			return
		
		start_date = datetime.strptime(str(self.repeat_start_date), "%Y-%m-%d")
		
		if self.repeat_frequency == "Daily":
			self.next_execution_date = start_date.date()
		elif self.repeat_frequency == "Weekly":
			self.next_execution_date = start_date.date()
		elif self.repeat_frequency == "Monthly":
			self.next_execution_date = start_date.date()
		else:
			self.next_execution_date = start_date.date()
	
	def create_work_session(self, execution_date=None):
		"""Create a Work Session from this template"""
		if not self.is_template:
			frappe.throw("Work Session은 템플릿에서만 생성할 수 있습니다.")
		
		if not execution_date:
			execution_date = self.next_execution_date or frappe.utils.today()
		
		# Create Work Session
		work_session = frappe.new_doc("Work Session")
		work_session.work_task = self.name
		work_session.work_project = self.work_project
		work_session.customer_site = self.customer_site
		work_session.checklist_template = self.checklist_template
		work_session.assigned_employee = self.assigned_employee
		work_session.work_date = execution_date
		work_session.estimated_duration = self.estimated_duration
		work_session.status = "Scheduled"
		work_session.description = self.description
		work_session.special_instructions = self.special_instructions
		
		# Set scheduled time
		if self.scheduled_start_time:
			scheduled_datetime = datetime.combine(
				datetime.strptime(str(execution_date), "%Y-%m-%d").date(),
				self.scheduled_start_time.time()
			)
			work_session.scheduled_start_time = scheduled_datetime
		
		work_session.insert()
		
		# Update session count
		self.total_sessions_created = (self.total_sessions_created or 0) + 1
		self.save()
		
		return work_session.name
	
	def get_next_execution_dates(self, count=30):
		"""Get next execution dates for this template"""
		if not self.is_template or not self.auto_repeat_enabled:
			return []
		
		dates = []
		current_date = datetime.strptime(str(self.repeat_start_date), "%Y-%m-%d")
		end_date = None
		
		if self.repeat_end_date:
			end_date = datetime.strptime(str(self.repeat_end_date), "%Y-%m-%d")
		
		for i in range(count):
			if end_date and current_date > end_date:
				break
			
			if self.should_execute_on_date(current_date):
				dates.append(current_date.date())
			
			# Move to next date based on frequency
			if self.repeat_frequency == "Daily":
				current_date += timedelta(days=1)
			elif self.repeat_frequency == "Weekly":
				current_date += timedelta(days=7)
			elif self.repeat_frequency == "Monthly":
				# Move to next month
				if current_date.month == 12:
					current_date = current_date.replace(year=current_date.year + 1, month=1)
				else:
					current_date = current_date.replace(month=current_date.month + 1)
			else:
				break
		
		return dates
	
	def should_execute_on_date(self, date):
		"""Check if task should execute on given date"""
		if not self.repeat_on_days:
			return True
		
		weekday = date.strftime("%A")
		
		if self.repeat_on_days == "월-금 (평일)":
			return weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
		elif self.repeat_on_days == "전체":
			return True
		else:
			return weekday == self.repeat_on_days
