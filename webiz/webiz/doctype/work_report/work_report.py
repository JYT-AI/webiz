# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class WorkReport(Document):
    def validate(self):
        self.calculate_total_hours()
        self.validate_times()
    
    def calculate_total_hours(self):
        """Calculate total hours from start and end time"""
        if self.actual_start_time and self.actual_end_time:
            start = frappe.utils.get_datetime(self.actual_start_time)
            end = frappe.utils.get_datetime(self.actual_end_time)
            
            if end > start:
                duration = end - start
                self.total_hours = duration.total_seconds() / 3600
            else:
                frappe.throw("종료 시간은 시작 시간보다 늦어야 합니다.")
    
    def validate_times(self):
        """Validate start and end times"""
        if self.actual_start_time and self.actual_end_time:
            start = frappe.utils.get_datetime(self.actual_start_time)
            end = frappe.utils.get_datetime(self.actual_end_time)
            
            if start > end:
                frappe.throw("시작 시간은 종료 시간보다 빨라야 합니다.")
    
    def on_submit(self):
        """Actions when work report is submitted"""
        # Update task status to "Completed" when report is submitted
        if self.task:
            task_doc = frappe.get_doc("Task", self.task)
            task_doc.status = "Completed"
            task_doc.save()
            
        # Create timesheet entry
        self.create_timesheet()
    
    def create_timesheet(self):
        """Create timesheet entry from work report"""
        if not self.assigned_to or not self.total_hours:
            return
            
        # Get project from task
        task_doc = frappe.get_doc("Task", self.task)
        project = task_doc.project
        
        timesheet = frappe.new_doc("Timesheet")
        timesheet.employee = self.assigned_to
        timesheet.start_date = frappe.utils.getdate(self.actual_start_time)
        timesheet.end_date = frappe.utils.getdate(self.actual_end_time)
        
        # Add time log
        timesheet.append("time_logs", {
            "activity_type": "현장작업",
            "from_time": self.actual_start_time,
            "to_time": self.actual_end_time,
            "hours": self.total_hours,
            "project": project,
            "task": self.task,
            "description": self.work_summary
        })
        
        timesheet.save()
        timesheet.submit()
        
        frappe.msgprint(f"Timesheet {timesheet.name} 이 생성되었습니다.")
