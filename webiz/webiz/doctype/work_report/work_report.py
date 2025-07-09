# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, today


class WorkReport(Document):
    def before_insert(self):
        """Set system fields and auto-populate data before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        self.generate_report_name()
        self.populate_session_data()
        self.generate_report_content()
        
    def before_save(self):
        """Set system fields before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
    def validate(self):
        """Validate the document"""
        self.validate_session()
        
    def generate_report_name(self):
        """Generate report name automatically"""
        if self.work_session:
            session = frappe.get_doc("Work Session", self.work_session)
            self.report_name = f"작업보고서 - {session.session_name}"
            
    def populate_session_data(self):
        """Populate data from work session"""
        if self.work_session:
            session = frappe.get_doc("Work Session", self.work_session)
            assignment = frappe.get_doc("Work Assignment", session.work_assignment)
            work_task = frappe.get_doc("Work Task", assignment.work_task)
            
            # Populate basic info
            self.worker = session.worker
            self.work_location = session.work_location
            self.work_duration = session.actual_duration
            self.contract = work_task.contract
            
            # Get customer from work site
            work_site = frappe.get_doc("Work Site", session.work_location)
            self.customer = work_site.customer
            
            # Calculate completion statistics
            self.total_items = len(session.checklist_items)
            self.completed_items = sum(1 for item in session.checklist_items if item.is_completed)
            self.completion_rate = session.completion_percentage
            
    def generate_report_content(self):
        """Generate work summary and completion details"""
        if self.work_session:
            session = frappe.get_doc("Work Session", self.work_session)
            assignment = frappe.get_doc("Work Assignment", session.work_assignment)
            work_task = frappe.get_doc("Work Task", assignment.work_task)
            
            # Generate work summary
            self.work_summary = f"""
작업명: {work_task.task_name}
작업장소: {session.work_location}
작업일: {session.session_date}
작업시간: {session.checkin_time} ~ {session.checkout_time}
소요시간: {session.actual_duration}분
완료율: {session.completion_percentage}%
            """.strip()
            
            # Generate completion details
            completed_items = []
            incomplete_items = []
            
            for item in session.checklist_items:
                if item.is_completed:
                    completed_items.append(f"✓ {item.item_name}")
                else:
                    incomplete_items.append(f"✗ {item.item_name}")
                    
            details = "=== 완료된 항목 ===\n"
            details += "\n".join(completed_items) if completed_items else "없음"
            
            if incomplete_items:
                details += "\n\n=== 미완료 항목 ===\n"
                details += "\n".join(incomplete_items)
                
            if session.worker_notes:
                details += f"\n\n=== 작업자 메모 ===\n{session.worker_notes}"
                
            self.completion_details = details
            
            # Collect attachments info
            attachments = []
            for item in session.checklist_items:
                if item.photo_attachment:
                    attachments.append(f"{item.item_name}: {item.photo_attachment}")
                    
            if attachments:
                self.attachments = "\n".join(attachments)
                
    def validate_session(self):
        """Validate work session"""
        if self.work_session:
            session = frappe.get_doc("Work Session", self.work_session)
            if session.session_status != "Completed":
                frappe.throw("완료되지 않은 세션에 대해서는 보고서를 생성할 수 없습니다.")
                
    def send_report(self):
        """Send report to customer"""
        if self.report_status != "Draft":
            frappe.throw("초안 상태의 보고서만 발송할 수 있습니다.")
            
        # Here you would implement email sending logic
        # For now, just update status
        self.report_status = "Sent"
        self.sent_date = now()
        self.save()
        
        frappe.msgprint("보고서가 성공적으로 발송되었습니다.")
        
    def mark_delivered(self):
        """Mark report as delivered"""
        if self.report_status != "Sent":
            frappe.throw("발송된 보고서만 배송완료로 표시할 수 있습니다.")
            
        self.report_status = "Delivered"
        self.save()
        
        frappe.msgprint("보고서가 배송완료로 표시되었습니다.")


@frappe.whitelist()
def create_work_report(work_session):
    """Create work report from work session"""
    # Check if report already exists
    existing = frappe.db.exists("Work Report", {"work_session": work_session})
    if existing:
        frappe.throw("이 세션에 대한 보고서가 이미 존재합니다.")
        
    # Create new report
    report = frappe.get_doc({
        "doctype": "Work Report",
        "work_session": work_session,
        "report_date": today()
    })
    report.insert()
    
    return report.name


@frappe.whitelist()
def send_work_report(report_name):
    """Send work report"""
    report = frappe.get_doc("Work Report", report_name)
    report.send_report()
    return {"status": "success"}


@frappe.whitelist()
def get_reports_by_customer(customer, from_date=None, to_date=None):
    """Get work reports for a specific customer"""
    filters = {"customer": customer}
    
    if from_date:
        filters["report_date"] = [">=", from_date]
    if to_date:
        if "report_date" in filters:
            filters["report_date"] = ["between", [from_date, to_date]]
        else:
            filters["report_date"] = ["<=", to_date]
            
    return frappe.get_all(
        "Work Report",
        filters=filters,
        fields=[
            "name", "report_name", "work_location", "worker", 
            "report_date", "completion_rate", "report_status"
        ],
        order_by="report_date desc"
    )


@frappe.whitelist()
def get_reports_by_location(work_location, from_date=None, to_date=None):
    """Get work reports for a specific location"""
    filters = {"work_location": work_location}
    
    if from_date:
        filters["report_date"] = [">=", from_date]
    if to_date:
        if "report_date" in filters:
            filters["report_date"] = ["between", [from_date, to_date]]
        else:
            filters["report_date"] = ["<=", to_date]
            
    return frappe.get_all(
        "Work Report",
        filters=filters,
        fields=[
            "name", "report_name", "worker", "report_date", 
            "completion_rate", "report_status", "work_duration"
        ],
        order_by="report_date desc"
    )
