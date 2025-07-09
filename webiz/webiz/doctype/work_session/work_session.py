# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, today, time_diff_in_hours, get_datetime
from datetime import datetime


class WorkSession(Document):
    def before_insert(self):
        """Set system fields and auto-populate data before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        self.generate_session_name()
        self.populate_assignment_data()
        self.populate_checklist_items()
        
    def before_save(self):
        """Set system fields and calculate values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        self.calculate_actual_duration()
        self.calculate_completion_percentage()
        
    def validate(self):
        """Validate the document"""
        self.validate_assignment()
        self.validate_times()
        
    def generate_session_name(self):
        """Generate session name automatically"""
        if self.work_assignment:
            assignment = frappe.get_doc("Work Assignment", self.work_assignment)
            work_task = frappe.get_doc("Work Task", assignment.work_task)
            self.session_name = f"{work_task.task_name} - {self.session_date}"
            
    def populate_assignment_data(self):
        """Populate data from work assignment"""
        if self.work_assignment:
            assignment = frappe.get_doc("Work Assignment", self.work_assignment)
            self.worker = assignment.assigned_to
            
            # Get work location from work task
            work_task = frappe.get_doc("Work Task", assignment.work_task)
            self.work_location = work_task.work_location
            
    def populate_checklist_items(self):
        """Populate checklist items from work template"""
        if self.work_assignment:
            assignment = frappe.get_doc("Work Assignment", self.work_assignment)
            work_task = frappe.get_doc("Work Task", assignment.work_task)
            template = frappe.get_doc("Work Template", work_task.checklist_template)
            
            # Clear existing items
            self.checklist_items = []
            
            # Add items from template
            for template_item in template.checklist_items:
                self.append("checklist_items", {
                    "item_name": template_item.item_name,
                    "is_mandatory": template_item.is_mandatory,
                    "is_completed": False
                })
                
    def validate_assignment(self):
        """Validate work assignment"""
        if self.work_assignment:
            assignment = frappe.get_doc("Work Assignment", self.work_assignment)
            if assignment.assignment_status not in ["Assigned", "In Progress"]:
                frappe.throw("완료되거나 취소된 할당에 대해서는 세션을 생성할 수 없습니다.")
                
    def validate_times(self):
        """Validate time fields"""
        if self.checkout_time and self.checkin_time:
            if self.checkout_time < self.checkin_time:
                frappe.throw("체크아웃 시간은 체크인 시간보다 늦어야 합니다.")
                
    def calculate_actual_duration(self):
        """Calculate actual duration in minutes"""
        if self.checkin_time and self.checkout_time:
            duration_hours = time_diff_in_hours(self.checkout_time, self.checkin_time)
            self.actual_duration = int(duration_hours * 60)
        else:
            self.actual_duration = 0
            
    def calculate_completion_percentage(self):
        """Calculate completion percentage based on checklist items"""
        if not self.checklist_items:
            self.completion_percentage = 0
            return
            
        total_items = len(self.checklist_items)
        completed_items = sum(1 for item in self.checklist_items if item.is_completed)
        
        self.completion_percentage = (completed_items / total_items) * 100 if total_items > 0 else 0
        
    def checkin(self):
        """Check in to start work session"""
        if self.session_status != "Started":
            frappe.throw("체크인은 시작된 세션에서만 가능합니다.")
            
        self.checkin_time = now()
        self.session_status = "In Progress"
        self.save()
        
        # Update assignment status
        assignment = frappe.get_doc("Work Assignment", self.work_assignment)
        assignment.assignment_status = "In Progress"
        assignment.save()
        
    def checkout(self):
        """Check out to complete work session"""
        if self.session_status != "In Progress":
            frappe.throw("체크아웃은 진행 중인 세션에서만 가능합니다.")
            
        # Check if all mandatory items are completed
        mandatory_incomplete = [
            item for item in self.checklist_items 
            if item.is_mandatory and not item.is_completed
        ]
        
        if mandatory_incomplete:
            incomplete_items = ", ".join([item.item_name for item in mandatory_incomplete])
            frappe.throw(f"다음 필수 항목들이 완료되지 않았습니다: {incomplete_items}")
            
        self.checkout_time = now()
        self.session_status = "Completed"
        self.save()
        
        # Update assignment status if this was the last session
        assignment = frappe.get_doc("Work Assignment", self.work_assignment)
        if assignment.recurrence_type == "None":
            assignment.assignment_status = "Completed"
            assignment.save()
            
        # Create work report
        self.create_work_report()
        
    def create_work_report(self):
        """Create work report after session completion"""
        if self.session_status == "Completed":
            report = frappe.get_doc({
                "doctype": "Work Report",
                "work_session": self.name,
                "report_date": today()
            })
            report.insert()
            return report.name
            
    def get_mandatory_items_status(self):
        """Get status of mandatory items"""
        mandatory_items = [item for item in self.checklist_items if item.is_mandatory]
        completed_mandatory = [item for item in mandatory_items if item.is_completed]
        
        return {
            "total_mandatory": len(mandatory_items),
            "completed_mandatory": len(completed_mandatory),
            "all_mandatory_completed": len(mandatory_items) == len(completed_mandatory)
        }


@frappe.whitelist()
def start_work_session(work_assignment, session_date=None):
    """Start a new work session"""
    if not session_date:
        session_date = today()
        
    # Check if session already exists for this assignment and date
    existing = frappe.db.exists("Work Session", {
        "work_assignment": work_assignment,
        "session_date": session_date
    })
    
    if existing:
        frappe.throw("이 날짜에 이미 세션이 존재합니다.")
        
    # Create new session
    session = frappe.get_doc({
        "doctype": "Work Session",
        "work_assignment": work_assignment,
        "session_date": session_date,
        "session_status": "Started"
    })
    session.insert()
    
    return session.name


@frappe.whitelist()
def checkin_session(session_name):
    """Check in to a work session"""
    session = frappe.get_doc("Work Session", session_name)
    session.checkin()
    return {"status": "success", "checkin_time": session.checkin_time}


@frappe.whitelist()
def checkout_session(session_name):
    """Check out from a work session"""
    session = frappe.get_doc("Work Session", session_name)
    session.checkout()
    return {"status": "success", "checkout_time": session.checkout_time}


@frappe.whitelist()
def update_checklist_item(session_name, item_idx, is_completed, notes=None):
    """Update a checklist item completion status"""
    session = frappe.get_doc("Work Session", session_name)
    
    if item_idx < len(session.checklist_items):
        item = session.checklist_items[item_idx]
        item.is_completed = is_completed
        if notes:
            item.notes = notes
        if is_completed:
            item.completion_time = now()
        else:
            item.completion_time = None
            
        session.save()
        return {"status": "success", "completion_percentage": session.completion_percentage}
    else:
        frappe.throw("잘못된 체크리스트 항목 인덱스입니다.")
