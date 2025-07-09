# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, today


class WorkTask(Document):
    def before_insert(self):
        """Set system fields before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Set system fields before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Validate dates
        if self.effective_to and self.effective_from:
            if self.effective_to < self.effective_from:
                frappe.throw("유효 종료일은 시작일보다 늦어야 합니다.")
                
    def validate(self):
        """Validate the document"""
        self.validate_contract_and_location()
        self.validate_template()
        
    def validate_contract_and_location(self):
        """Validate that contract and work location are compatible"""
        if self.contract and self.work_location:
            # Get customer from work location
            work_site = frappe.get_doc("Work Site", self.work_location)
            location_customer = work_site.customer
            
            # Get customer from contract
            contract = frappe.get_doc("Contract", self.contract)
            contract_customer = contract.party_name if contract.party_type == "Customer" else None
            
            if location_customer != contract_customer:
                frappe.throw(f"계약의 고객사({contract_customer})와 작업장소의 고객사({location_customer})가 일치하지 않습니다.")
                
    def validate_template(self):
        """Validate checklist template"""
        if self.checklist_template:
            template = frappe.get_doc("Work Template", self.checklist_template)
            if template.status != "Active":
                frappe.throw("비활성화된 체크리스트 템플릿은 사용할 수 없습니다.")
                
    def get_active_assignments(self):
        """Get active work assignments for this task"""
        return frappe.get_all(
            "Work Assignment",
            filters={
                "work_task": self.name,
                "assignment_status": ["in", ["Assigned", "In Progress"]]
            },
            fields=["name", "assigned_to", "assignment_date", "assignment_status"]
        )
        
    def get_completion_stats(self):
        """Get completion statistics for this task"""
        total_sessions = frappe.db.count("Work Session", {"work_task": self.name})
        completed_sessions = frappe.db.count("Work Session", {
            "work_task": self.name,
            "session_status": "Completed"
        })
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        }


@frappe.whitelist()
def get_work_tasks_by_location(work_location):
    """Get all active work tasks for a specific location"""
    return frappe.get_all(
        "Work Task",
        filters={
            "work_location": work_location,
            "status": "Active",
            "effective_from": ["<=", today()],
            "effective_to": [">=", today()]
        },
        fields=["name", "task_name", "estimated_duration", "priority", "checklist_template"]
    )


@frappe.whitelist()
def get_work_tasks_by_contract(contract):
    """Get all work tasks for a specific contract"""
    return frappe.get_all(
        "Work Task",
        filters={"contract": contract},
        fields=["name", "task_name", "work_location", "status", "effective_from", "effective_to"]
    )
