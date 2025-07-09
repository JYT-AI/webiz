# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, get_datetime, time_diff_in_hours, flt
from frappe import _
import json


class WorkAssignment(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        self.assigned_by = frappe.session.user
        
        # Auto-generate title if not provided
        if not self.assignment_title:
            self.assignment_title = f"{self.work_type_name} - {self.area_name}"
        
    def before_save(self):
        """Validate and set values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Calculate actual hours if start and end times are set
        if self.start_time and self.end_time:
            total_hours = time_diff_in_hours(self.end_time, self.start_time)
            if self.break_duration:
                total_hours -= (self.break_duration / 60)  # Convert minutes to hours
            self.actual_hours = max(0, total_hours)
        
        # Auto-set completion date when status changes to Completed
        if self.status == "Completed" and not self.completion_date:
            self.completion_date = getdate()
            
        # Calculate progress percentage based on status
        self.update_progress_percentage()
        
        # Update efficiency rating
        if self.estimated_hours and self.actual_hours:
            if self.actual_hours <= self.estimated_hours:
                self.efficiency_rating = 5  # Excellent
            elif self.actual_hours <= self.estimated_hours * 1.2:
                self.efficiency_rating = 4  # Good
            elif self.actual_hours <= self.estimated_hours * 1.5:
                self.efficiency_rating = 3  # Average
            elif self.actual_hours <= self.estimated_hours * 2:
                self.efficiency_rating = 2  # Below Average
            else:
                self.efficiency_rating = 1  # Poor
    
    def validate(self):
        """Additional validation"""
        # Validate dates
        if self.assignment_date and self.due_date:
            if getdate(self.assignment_date) > getdate(self.due_date):
                frappe.throw(_("할당일은 완료 예정일보다 늦을 수 없습니다"))
                
        if self.completion_date and self.assignment_date:
            if getdate(self.completion_date) < getdate(self.assignment_date):
                frappe.throw(_("완료일은 할당일보다 빠를 수 없습니다"))
        
        # Validate time tracking
        if self.start_time and self.end_time:
            if get_datetime(self.start_time) >= get_datetime(self.end_time):
                frappe.throw(_("시작 시간은 종료 시간보다 빨라야 합니다"))
        
        # Check if work area and work type combination exists in Area Work Type
        if self.work_area and self.work_type:
            area_work_type = frappe.db.get_value("Area Work Type", 
                {"work_area": self.work_area, "work_type": self.work_type, "is_active": 1}, 
                "name")
            if area_work_type:
                self.area_work_type = area_work_type
    
    def update_progress_percentage(self):
        """Update progress percentage based on status"""
        status_progress = {
            "Assigned": 0,
            "In Progress": 50,
            "Completed": 100,
            "Cancelled": 0,
            "On Hold": 25,
            "Overdue": 10
        }
        self.progress_percentage = status_progress.get(self.status, 0)
    
    def on_update(self):
        """Actions to perform after update"""
        # Auto-create checklist if enabled
        if self.auto_create_checklist and self.checklist_template and not self.work_checklist:
            self.create_work_checklist()
            
        # Update status to overdue if past due date
        if self.status not in ["Completed", "Cancelled"] and self.due_date:
            if getdate() > getdate(self.due_date):
                self.status = "Overdue"
                self.save()
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_assignment",
            "transactions": [
                {
                    "label": _("관련 문서"),
                    "items": ["Work Checklist", "Worker Checkin"]
                }
            ]
        }
    
    @frappe.whitelist()
    def start_work(self, gps_coordinates=None):
        """Start work on this assignment"""
        if self.status != "Assigned":
            return {
                "status": "error",
                "message": _("할당된 상태의 작업만 시작할 수 있습니다")
            }
        
        try:
            self.status = "In Progress"
            self.start_time = now()
            if gps_coordinates:
                self.gps_coordinates = gps_coordinates
                self.location_verified = 1
            
            self.save()
            
            return {
                "status": "success",
                "message": _("작업이 시작되었습니다")
            }
            
        except Exception as e:
            frappe.log_error(f"Work start failed: {str(e)}")
            return {
                "status": "error",
                "message": _("작업 시작에 실패했습니다")
            }
    
    @frappe.whitelist()
    def complete_work(self, completion_notes=None, photo_evidence=None):
        """Complete this work assignment"""
        if self.status not in ["In Progress", "Assigned"]:
            return {
                "status": "error",
                "message": _("진행 중이거나 할당된 상태의 작업만 완료할 수 있습니다")
            }
        
        try:
            self.status = "Completed"
            self.end_time = now()
            self.completion_date = getdate()
            
            if completion_notes:
                self.completion_notes = completion_notes
            if photo_evidence:
                self.photo_evidence = photo_evidence
            
            # Check if approval is required
            if self.requires_approval:
                self.approval_status = "Pending"
                self.status = "Completed"  # Still mark as completed but pending approval
            
            self.save()
            
            return {
                "status": "success",
                "message": _("작업이 완료되었습니다")
            }
            
        except Exception as e:
            frappe.log_error(f"Work completion failed: {str(e)}")
            return {
                "status": "error",
                "message": _("작업 완료에 실패했습니다")
            }
    
    @frappe.whitelist()
    def create_work_checklist(self):
        """Create a work checklist from the template"""
        if not self.checklist_template:
            return {
                "status": "error",
                "message": _("체크리스트 템플릿이 설정되지 않았습니다")
            }
        
        if self.work_checklist:
            return {
                "status": "error",
                "message": _("이미 체크리스트가 생성되어 있습니다")
            }
        
        try:
            template = frappe.get_doc("Checklist Template", self.checklist_template)
            result = template.create_checklist(
                work_area=self.work_area,
                assigned_to=self.assigned_to,
                due_date=self.due_date,
                work_site=frappe.db.get_value("Work Area", self.work_area, "work_site")
            )
            
            if result["status"] == "success":
                self.work_checklist = result["checklist_name"]
                self.save()
                
            return result
            
        except Exception as e:
            frappe.log_error(f"Checklist creation failed: {str(e)}")
            return {
                "status": "error",
                "message": _("체크리스트 생성에 실패했습니다")
            }
    
    @frappe.whitelist()
    def approve_work(self, approval_notes=None):
        """Approve completed work"""
        if self.status != "Completed" or self.approval_status != "Pending":
            return {
                "status": "error",
                "message": _("승인 대기 중인 완료된 작업만 승인할 수 있습니다")
            }
        
        try:
            self.approval_status = "Approved"
            self.approved_by = frappe.session.user
            if approval_notes:
                self.supervisor_notes = approval_notes
            
            self.save()
            
            return {
                "status": "success",
                "message": _("작업이 승인되었습니다")
            }
            
        except Exception as e:
            frappe.log_error(f"Work approval failed: {str(e)}")
            return {
                "status": "error",
                "message": _("작업 승인에 실패했습니다")
            }
    
    @frappe.whitelist()
    def get_time_tracking_summary(self):
        """Get time tracking summary"""
        summary = {
            "estimated_hours": self.estimated_hours or 0,
            "actual_hours": self.actual_hours or 0,
            "break_duration_hours": (self.break_duration or 0) / 60,
            "efficiency_rating": self.efficiency_rating or 0,
            "is_overdue": False,
            "days_overdue": 0
        }
        
        if self.due_date and getdate() > getdate(self.due_date):
            summary["is_overdue"] = True
            summary["days_overdue"] = (getdate() - getdate(self.due_date)).days
        
        if summary["estimated_hours"] > 0:
            summary["efficiency_percentage"] = round(
                (summary["estimated_hours"] / summary["actual_hours"] * 100), 2
            ) if summary["actual_hours"] > 0 else 0
        
        return summary


@frappe.whitelist()
def get_assignments_by_worker(employee, status=None, limit=20):
    """Get assignments for a specific worker"""
    filters = {"assigned_to": employee}
    if status:
        filters["status"] = status
        
    return frappe.get_all("Work Assignment",
        filters=filters,
        fields=["name", "assignment_title", "work_area", "area_name", "work_type_name", 
                "assignment_date", "due_date", "status", "priority", "progress_percentage"],
        order_by="assignment_date desc",
        limit=limit
    )


@frappe.whitelist()
def get_assignments_by_area(work_area, status=None, limit=20):
    """Get assignments for a specific work area"""
    filters = {"work_area": work_area}
    if status:
        filters["status"] = status
        
    return frappe.get_all("Work Assignment",
        filters=filters,
        fields=["name", "assignment_title", "assigned_to", "assigned_to_name", "work_type_name",
                "assignment_date", "due_date", "status", "priority", "progress_percentage"],
        order_by="assignment_date desc",
        limit=limit
    )


@frappe.whitelist()
def get_overdue_assignments():
    """Get all overdue assignments"""
    return frappe.db.sql("""
        SELECT name, assignment_title, assigned_to, assigned_to_name, work_area, area_name,
               work_type_name, due_date, status, priority,
               DATEDIFF(CURDATE(), due_date) as days_overdue
        FROM `tabWork Assignment`
        WHERE status NOT IN ('Completed', 'Cancelled')
        AND due_date < CURDATE()
        ORDER BY days_overdue DESC, priority DESC
    """, as_dict=True)


@frappe.whitelist()
def get_assignment_statistics(date_range=30):
    """Get assignment statistics for dashboard"""
    from_date = frappe.utils.add_days(getdate(), -date_range)
    
    stats = {}
    
    # Total assignments
    stats["total"] = frappe.db.count("Work Assignment", {
        "assignment_date": [">=", from_date]
    })
    
    # By status
    for status in ["Assigned", "In Progress", "Completed", "Overdue", "Cancelled"]:
        stats[status.lower().replace(" ", "_")] = frappe.db.count("Work Assignment", {
            "status": status,
            "assignment_date": [">=", from_date]
        })
    
    # Completion rate
    completed = stats.get("completed", 0)
    total_actionable = stats["total"] - stats.get("cancelled", 0)
    stats["completion_rate"] = round((completed / total_actionable * 100), 2) if total_actionable > 0 else 0
    
    # Average efficiency
    avg_efficiency = frappe.db.sql("""
        SELECT AVG(efficiency_rating) as avg_rating
        FROM `tabWork Assignment`
        WHERE status = 'Completed'
        AND assignment_date >= %s
        AND efficiency_rating > 0
    """, (from_date,), as_dict=True)
    
    stats["avg_efficiency"] = round(avg_efficiency[0].avg_rating, 2) if avg_efficiency and avg_efficiency[0].avg_rating else 0
    
    return stats
