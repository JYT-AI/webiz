# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, today, add_days, get_weekday, getdate
from datetime import datetime, timedelta


class WorkAssignment(Document):
    def before_insert(self):
        """Set system fields and generate assignment name before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        self.generate_assignment_name()
        
    def before_save(self):
        """Set system fields before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Auto-populate estimated duration from work task if not set
        if not self.estimated_duration and self.work_task:
            work_task = frappe.get_doc("Work Task", self.work_task)
            self.estimated_duration = work_task.estimated_duration
            
    def validate(self):
        """Validate the document"""
        self.validate_dates()
        self.validate_work_task()
        self.validate_employee()
        
    def generate_assignment_name(self):
        """Generate assignment name automatically"""
        if self.work_task and self.assigned_to:
            work_task = frappe.get_doc("Work Task", self.work_task)
            employee = frappe.get_doc("Employee", self.assigned_to)
            self.assignment_name = f"{work_task.task_name} - {employee.employee_name}"
            
    def validate_dates(self):
        """Validate date fields"""
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                frappe.throw("종료일은 시작일보다 늦어야 합니다.")
                
        if self.assignment_date > self.start_date:
            frappe.throw("할당일은 시작일보다 이르거나 같아야 합니다.")
            
    def validate_work_task(self):
        """Validate work task"""
        if self.work_task:
            work_task = frappe.get_doc("Work Task", self.work_task)
            if work_task.status != "Active":
                frappe.throw("비활성화된 작업은 할당할 수 없습니다.")
                
            # Check if task is within effective dates
            if work_task.effective_from > self.start_date:
                frappe.throw(f"작업 시작일({self.start_date})이 작업 유효 시작일({work_task.effective_from})보다 빠릅니다.")
                
            if work_task.effective_to and work_task.effective_to < self.start_date:
                frappe.throw(f"작업 시작일({self.start_date})이 작업 유효 종료일({work_task.effective_to})보다 늦습니다.")
                
    def validate_employee(self):
        """Validate employee"""
        if self.assigned_to:
            employee = frappe.get_doc("Employee", self.assigned_to)
            if employee.status != "Active":
                frappe.throw("비활성화된 직원에게는 작업을 할당할 수 없습니다.")
                
    def get_work_sessions(self):
        """Get all work sessions for this assignment"""
        return frappe.get_all(
            "Work Session",
            filters={"work_assignment": self.name},
            fields=["name", "session_date", "session_status", "completion_percentage"]
        )
        
    def get_next_scheduled_date(self):
        """Get next scheduled date based on recurrence"""
        if self.recurrence_type == "None" or not self.recurrence_type:
            return None
            
        last_session = frappe.get_all(
            "Work Session",
            filters={"work_assignment": self.name},
            fields=["session_date"],
            order_by="session_date desc",
            limit=1
        )
        
        base_date = getdate(last_session[0].session_date) if last_session else getdate(self.start_date)
        
        if self.recurrence_type == "Daily":
            return add_days(base_date, 1)
        elif self.recurrence_type == "Weekly":
            return add_days(base_date, 7)
        elif self.recurrence_type == "Monthly":
            return add_days(base_date, 30)  # Simplified monthly calculation
            
        return None


@frappe.whitelist()
def get_employee_assignments(employee, date=None):
    """Get assignments for a specific employee on a specific date"""
    if not date:
        date = today()
        
    return frappe.get_all(
        "Work Assignment",
        filters={
            "assigned_to": employee,
            "start_date": ["<=", date],
            "assignment_status": ["in", ["Assigned", "In Progress"]]
        },
        fields=[
            "name", "assignment_name", "work_task", "start_date", 
            "scheduled_time", "estimated_duration", "assignment_status"
        ]
    )


@frappe.whitelist()
def get_location_assignments(work_location, date=None):
    """Get all assignments for a specific location on a specific date"""
    if not date:
        date = today()
        
    # Get work tasks for this location
    work_tasks = frappe.get_all(
        "Work Task",
        filters={"work_location": work_location},
        fields=["name"]
    )
    
    if not work_tasks:
        return []
        
    task_names = [task.name for task in work_tasks]
    
    return frappe.get_all(
        "Work Assignment",
        filters={
            "work_task": ["in", task_names],
            "start_date": ["<=", date],
            "assignment_status": ["in", ["Assigned", "In Progress"]]
        },
        fields=[
            "name", "assignment_name", "work_task", "assigned_to", 
            "start_date", "scheduled_time", "assignment_status"
        ]
    )


@frappe.whitelist()
def create_recurring_assignments():
    """Create recurring assignments based on recurrence settings"""
    # Get all assignments with recurrence that need new instances
    assignments = frappe.get_all(
        "Work Assignment",
        filters={
            "recurrence_type": ["!=", "None"],
            "assignment_status": ["in", ["Assigned", "In Progress"]]
        },
        fields=["name", "recurrence_type", "start_date", "end_date"]
    )
    
    created_count = 0
    
    for assignment_data in assignments:
        assignment = frappe.get_doc("Work Assignment", assignment_data.name)
        next_date = assignment.get_next_scheduled_date()
        
        if next_date and (not assignment.end_date or next_date <= getdate(assignment.end_date)):
            # Check if assignment already exists for this date
            existing = frappe.db.exists("Work Assignment", {
                "work_task": assignment.work_task,
                "assigned_to": assignment.assigned_to,
                "start_date": next_date
            })
            
            if not existing:
                # Create new assignment
                new_assignment = frappe.copy_doc(assignment)
                new_assignment.start_date = next_date
                new_assignment.assignment_date = today()
                new_assignment.assignment_status = "Assigned"
                new_assignment.insert()
                created_count += 1
                
    return {"created": created_count}
