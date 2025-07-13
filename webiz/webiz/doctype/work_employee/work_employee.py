# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkEmployee(Document):
	def validate(self):
		"""Validate Work Employee data"""
		self.validate_employee()
		self.validate_work_hours()
	
	def validate_employee(self):
		"""Validate employee exists and is active"""
		if self.employee:
			employee_doc = frappe.get_doc("Employee", self.employee)
			if employee_doc.status != "Active":
				frappe.throw(f"직원 {self.employee_name}은(는) 비활성 상태입니다.")
	
	def validate_work_hours(self):
		"""Validate work hours"""
		if self.max_hours_per_day and self.max_hours_per_day > 24:
			frappe.throw("일일 최대 근무시간은 24시간을 초과할 수 없습니다.")
		
		if self.max_hours_per_day and self.max_hours_per_day < 0:
			frappe.throw("일일 최대 근무시간은 0보다 커야 합니다.")
	
	def before_save(self):
		"""Before save operations"""
		self.update_workload_stats()
	
	def update_workload_stats(self):
		"""Update current workload and statistics"""
		# Count active work sessions assigned to this employee
		active_sessions = frappe.db.count("Work Session", {
			"assigned_employee": self.employee,
			"status": ["in", ["Scheduled", "In Progress"]]
		})
		self.current_workload = active_sessions
		
		# Get total work sessions
		total_sessions = frappe.db.count("Work Session", {
			"assigned_employee": self.employee
		})
		self.total_work_sessions = total_sessions
		
		# Get last work date
		last_session = frappe.db.get_value("Work Session", {
			"assigned_employee": self.employee,
			"status": "Completed"
		}, "work_date", order_by="work_date desc")
		
		if last_session:
			self.last_work_date = last_session
		
		# Update average rating
		self.update_average_rating()
	
	def update_average_rating(self):
		"""Update average rating from completed work sessions"""
		ratings = frappe.db.get_all("Work Session", {
			"assigned_employee": self.employee,
			"status": "Completed",
			"quality_rating": ["is", "set"]
		}, ["quality_rating"])
		
		if ratings:
			total_rating = sum([float(r.quality_rating) for r in ratings if r.quality_rating])
			self.total_ratings = len(ratings)
			self.average_rating = total_rating / len(ratings) if ratings else 0
		else:
			self.total_ratings = 0
			self.average_rating = 0
	
	def get_availability_for_date(self, date):
		"""Check if employee is available on given date"""
		import datetime
		
		# Check if employee is active
		if self.status != "Active":
			return False
		
		# Check day of week availability
		weekday = datetime.datetime.strptime(str(date), "%Y-%m-%d").strftime("%A")
		
		if self.available_days == "월-금" and weekday in ["Saturday", "Sunday"]:
			return False
		elif self.available_days == "월-토" and weekday == "Sunday":
			return False
		
		# Check current workload
		daily_sessions = frappe.db.count("Work Session", {
			"assigned_employee": self.employee,
			"work_date": date,
			"status": ["in", ["Scheduled", "In Progress"]]
		})
		
		# Assume each session is 4 hours on average if not specified
		estimated_hours = daily_sessions * 4
		if estimated_hours >= self.max_hours_per_day:
			return False
		
		return True
	
	def get_workload_for_period(self, start_date, end_date):
		"""Get workload statistics for a period"""
		sessions = frappe.db.get_all("Work Session", {
			"assigned_employee": self.employee,
			"work_date": ["between", [start_date, end_date]]
		}, ["work_date", "status", "actual_duration", "quality_rating"])
		
		stats = {
			"total_sessions": len(sessions),
			"completed_sessions": len([s for s in sessions if s.status == "Completed"]),
			"total_hours": sum([s.actual_duration or 0 for s in sessions]),
			"average_rating": 0
		}
		
		ratings = [s.quality_rating for s in sessions if s.quality_rating]
		if ratings:
			stats["average_rating"] = sum([float(r) for r in ratings]) / len(ratings)
		
		return stats
	
	@frappe.whitelist()
	def get_schedule(self, start_date, end_date):
		"""Get employee schedule for date range"""
		sessions = frappe.db.get_all("Work Session", {
			"assigned_employee": self.employee,
			"work_date": ["between", [start_date, end_date]]
		}, ["name", "work_date", "scheduled_start_time", "customer_site", 
		    "status", "estimated_duration", "work_task"])
		
		schedule = []
		for session in sessions:
			site_name = frappe.db.get_value("Customer Site", session.customer_site, "site_name")
			task_title = frappe.db.get_value("Work Task", session.work_task, "title")
			
			schedule.append({
				"session_name": session.name,
				"date": session.work_date,
				"start_time": session.scheduled_start_time,
				"site": site_name,
				"task": task_title,
				"status": session.status,
				"duration": session.estimated_duration
			})
		
		return schedule
