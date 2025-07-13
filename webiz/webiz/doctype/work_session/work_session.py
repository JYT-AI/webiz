# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import json


class WorkSession(Document):
	def validate(self):
		"""Validate Work Session data"""
		self.validate_times()
		self.validate_employee_assignment()
	
	def validate_times(self):
		"""Validate time fields"""
		if self.actual_start_time and self.actual_end_time:
			if self.actual_start_time >= self.actual_end_time:
				frappe.throw("실제 시작 시간은 종료 시간보다 이전이어야 합니다.")
		
		if self.check_in_time and self.check_out_time:
			if self.check_in_time >= self.check_out_time:
				frappe.throw("체크인 시간은 체크아웃 시간보다 이전이어야 합니다.")
	
	def validate_employee_assignment(self):
		"""Validate employee assignment"""
		if self.assigned_employee:
			# Check if employee is available on work date
			work_employee = frappe.db.get_value("Work Employee", 
				{"employee": self.assigned_employee}, "name")
			
			if work_employee:
				work_emp_doc = frappe.get_doc("Work Employee", work_employee)
				if not work_emp_doc.get_availability_for_date(self.work_date):
					frappe.msgprint(f"직원 {self.employee_name}은(는) {self.work_date}에 근무할 수 없습니다.")
	
	def before_save(self):
		"""Before save operations"""
		self.set_title()
		self.calculate_durations()
		self.update_status_based_on_times()
		self.load_checklist_items()
	
	def set_title(self):
		"""Set title based on work task and date"""
		if self.work_task and self.work_date:
			task_doc = frappe.get_doc("Work Task", self.work_task)
			self.title = f"{task_doc.title} - {self.work_date}"
	
	def calculate_durations(self):
		"""Calculate actual duration and billable hours"""
		if self.actual_start_time and self.actual_end_time:
			start = datetime.strptime(str(self.actual_start_time), "%Y-%m-%d %H:%M:%S")
			end = datetime.strptime(str(self.actual_end_time), "%Y-%m-%d %H:%M:%S")
			duration = (end - start).total_seconds() / 3600  # Convert to hours
			
			self.actual_duration = duration
			
			# Calculate billable hours (actual duration - break duration)
			self.total_billable_hours = duration - (self.break_duration or 0)
			
			# Calculate overtime (if actual duration > estimated duration)
			if self.estimated_duration and duration > self.estimated_duration:
				self.overtime_hours = duration - self.estimated_duration
			else:
				self.overtime_hours = 0
	
	def update_status_based_on_times(self):
		"""Update status based on time fields"""
		if self.check_in_time and not self.check_out_time:
			if self.status == "Scheduled":
				self.status = "In Progress"
		elif self.check_out_time and self.actual_end_time:
			if self.status in ["Scheduled", "In Progress"]:
				self.status = "Completed"
	
	def load_checklist_items(self):
		"""Load checklist items from template if not already loaded"""
		if self.checklist_template and not self.checklist_results:
			template_doc = frappe.get_doc("Facility Checklist Template", self.checklist_template)
			
			for item in template_doc.checklist_items:
				checklist_result = {
					"checklist_item": item.item_name,
					"description": item.description,
					"is_mandatory": item.is_mandatory,
					"status": "Pending"
				}
				self.append("checklist_results", checklist_result)
	
	@frappe.whitelist()
	def start_work(self, check_in_location=None):
		"""Start work session"""
		if self.status != "Scheduled":
			frappe.throw("예정된 작업만 시작할 수 있습니다.")
		
		now = frappe.utils.now()
		self.check_in_time = now
		self.actual_start_time = now
		self.status = "In Progress"
		
		# Create attendance record if not exists
		self.create_attendance_record(check_in_location)
		
		self.save()
		frappe.msgprint("작업이 시작되었습니다.")
	
	@frappe.whitelist()
	def complete_work(self, check_out_location=None):
		"""Complete work session"""
		if self.status != "In Progress":
			frappe.throw("진행 중인 작업만 완료할 수 있습니다.")
		
		# Validate checklist completion
		mandatory_items = [item for item in self.checklist_results if item.is_mandatory]
		incomplete_mandatory = [item for item in mandatory_items if item.status != "Completed"]
		
		if incomplete_mandatory:
			frappe.throw("필수 체크리스트 항목을 모두 완료해야 합니다.")
		
		now = frappe.utils.now()
		self.check_out_time = now
		self.actual_end_time = now
		self.status = "Completed"
		
		# Update attendance record
		self.update_attendance_record(check_out_location)
		
		# Create/update timesheet
		self.create_or_update_timesheet()
		
		self.save()
		frappe.msgprint("작업이 완료되었습니다.")
	
	def create_attendance_record(self, check_in_location=None):
		"""Create attendance record for work session"""
		if not self.assigned_employee:
			return
		
		# Check if attendance already exists for this date
		existing_attendance = frappe.db.get_value("Attendance", {
			"employee": self.assigned_employee,
			"attendance_date": self.work_date
		}, "name")
		
		if not existing_attendance:
			attendance = frappe.new_doc("Attendance")
			attendance.employee = self.assigned_employee
			attendance.attendance_date = self.work_date
			attendance.status = "Present"
			attendance.in_time = self.check_in_time
			
			# Add custom fields if they exist
			if check_in_location:
				attendance.check_in_location = check_in_location
			
			attendance.insert()
	
	def update_attendance_record(self, check_out_location=None):
		"""Update attendance record with check out info"""
		if not self.assigned_employee:
			return
		
		attendance = frappe.db.get_value("Attendance", {
			"employee": self.assigned_employee,
			"attendance_date": self.work_date
		}, "name")
		
		if attendance:
			attendance_doc = frappe.get_doc("Attendance", attendance)
			attendance_doc.out_time = self.check_out_time
			
			# Add custom fields if they exist
			if check_out_location:
				attendance_doc.check_out_location = check_out_location
			
			attendance_doc.save()
	
	def create_or_update_timesheet(self):
		"""Create or update timesheet entry"""
		if not self.assigned_employee or not self.total_billable_hours:
			return
		
		# Find existing timesheet for this date and employee
		existing_timesheet = frappe.db.get_value("Timesheet", {
			"employee": self.assigned_employee,
			"start_date": self.work_date,
			"docstatus": ["<", 2]
		}, "name")
		
		if existing_timesheet:
			timesheet_doc = frappe.get_doc("Timesheet", existing_timesheet)
		else:
			timesheet_doc = frappe.new_doc("Timesheet")
			timesheet_doc.employee = self.assigned_employee
			timesheet_doc.start_date = self.work_date
			timesheet_doc.end_date = self.work_date
		
		# Add or update time log entry
		existing_log = None
		for log in timesheet_doc.time_logs:
			if log.get("work_session") == self.name:
				existing_log = log
				break
		
		if not existing_log:
			timesheet_doc.append("time_logs", {
				"activity_type": "시설관리",
				"from_time": self.actual_start_time,
				"to_time": self.actual_end_time,
				"hours": self.total_billable_hours,
				"project": frappe.db.get_value("Work Project", self.work_project, "project"),
				"work_session": self.name
			})
		else:
			existing_log.from_time = self.actual_start_time
			existing_log.to_time = self.actual_end_time
			existing_log.hours = self.total_billable_hours
		
		timesheet_doc.save()
		self.timesheet = timesheet_doc.name
	
	@frappe.whitelist()
	def update_checklist_item(self, item_name, status, notes=None, photo=None):
		"""Update checklist item status"""
		for item in self.checklist_results:
			if item.checklist_item == item_name:
				item.status = status
				if notes:
					item.notes = notes
				if photo:
					item.completion_photo = photo
				break

		self.save()
		return "체크리스트 항목이 업데이트되었습니다."

	def get_completion_percentage(self):
		"""Get checklist completion percentage"""
		if not self.checklist_results:
			return 0

		total_items = len(self.checklist_results)
		completed_items = len([item for item in self.checklist_results if item.status == "Completed"])

		return (completed_items / total_items) * 100 if total_items > 0 else 0

	@frappe.whitelist()
	def get_mobile_view_data(self):
		"""Get data optimized for mobile view"""
		return {
			"session_info": {
				"name": self.name,
				"title": self.title,
				"status": self.status,
				"work_date": self.work_date,
				"site_name": frappe.db.get_value("Customer Site", self.customer_site, "site_name"),
				"estimated_duration": self.estimated_duration,
				"scheduled_start_time": self.scheduled_start_time
			},
			"checklist": [
				{
					"item": item.checklist_item,
					"description": item.description,
					"is_mandatory": item.is_mandatory,
					"status": item.status,
					"notes": item.get("notes", "")
				}
				for item in self.checklist_results
			],
			"completion_percentage": self.get_completion_percentage()
		}
