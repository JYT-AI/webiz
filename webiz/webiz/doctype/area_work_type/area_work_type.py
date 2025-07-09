# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt
from frappe import _


class AreaWorkType(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and set values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Validate duration
        if self.estimated_duration_hours and self.estimated_duration_hours < 0:
            frappe.throw(_("예상 소요시간(시간)은 음수일 수 없습니다"))
            
        if self.estimated_duration_minutes and (self.estimated_duration_minutes < 0 or self.estimated_duration_minutes >= 60):
            frappe.throw(_("예상 소요시간(분)은 0-59 사이여야 합니다"))
            
        # Validate dates
        if self.effective_date and self.expiry_date:
            if getdate(self.effective_date) > getdate(self.expiry_date):
                frappe.throw(_("시작일은 종료일보다 늦을 수 없습니다"))
    
    def validate(self):
        """Additional validation"""
        # Check if work area exists
        if self.work_area and not frappe.db.exists("Work Area", self.work_area):
            frappe.throw(_("작업구역 '{0}'이 존재하지 않습니다").format(self.work_area))
            
        # Check if work type exists
        if self.work_type and not frappe.db.exists("Work Type", self.work_type):
            frappe.throw(_("업무유형 '{0}'이 존재하지 않습니다").format(self.work_type))
            
        # Check for duplicate mapping
        existing = frappe.db.get_value("Area Work Type", 
            {
                "work_area": self.work_area, 
                "work_type": self.work_type, 
                "name": ["!=", self.name]
            }, 
            "name")
        if existing:
            frappe.throw(_("작업구역 '{0}'과 업무유형 '{1}'의 매핑이 이미 존재합니다").format(
                self.work_area, self.work_type))
                
        # Validate checklist template
        if self.checklist_template and not frappe.db.exists("Checklist Template", self.checklist_template):
            frappe.throw(_("체크리스트 템플릿 '{0}'이 존재하지 않습니다").format(self.checklist_template))
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "area_work_type",
            "transactions": [
                {
                    "label": _("작업 관리"),
                    "items": ["Work Assignment", "Work Checklist"]
                }
            ]
        }
    
    @frappe.whitelist()
    def get_total_duration_minutes(self):
        """Get total duration in minutes"""
        total_minutes = 0
        if self.estimated_duration_hours:
            total_minutes += self.estimated_duration_hours * 60
        if self.estimated_duration_minutes:
            total_minutes += self.estimated_duration_minutes
        return total_minutes
    
    @frappe.whitelist()
    def get_formatted_duration(self):
        """Get formatted duration string"""
        duration_parts = []
        if self.estimated_duration_hours:
            duration_parts.append(f"{self.estimated_duration_hours}시간")
        if self.estimated_duration_minutes:
            duration_parts.append(f"{self.estimated_duration_minutes}분")
        
        if duration_parts:
            return " ".join(duration_parts)
        else:
            return "미설정"
    
    @frappe.whitelist()
    def is_valid_for_date(self, check_date=None):
        """Check if this mapping is valid for a specific date"""
        if not check_date:
            check_date = getdate()
        else:
            check_date = getdate(check_date)
            
        # Check if active
        if not self.is_active:
            return False
            
        # Check effective date
        if self.effective_date and check_date < getdate(self.effective_date):
            return False
            
        # Check expiry date
        if self.expiry_date and check_date > getdate(self.expiry_date):
            return False
            
        return True
    
    @frappe.whitelist()
    def create_work_assignment(self, assigned_to, due_date=None, notes=None):
        """Create a work assignment from this area work type mapping"""
        try:
            assignment = frappe.get_doc({
                "doctype": "Work Assignment",
                "work_area": self.work_area,
                "work_type": self.work_type,
                "area_work_type": self.name,
                "assigned_to": assigned_to,
                "assigned_by": frappe.session.user,
                "assignment_date": getdate(),
                "due_date": due_date or getdate(),
                "status": "Assigned",
                "priority": self.priority_level,
                "estimated_hours": self.get_total_duration_minutes() / 60 if self.get_total_duration_minutes() else None,
                "special_requirements": self.special_requirements,
                "notes": notes,
                "checklist_template": self.checklist_template,
                "auto_create_checklist": self.auto_create_checklist,
                "requires_approval": self.requires_approval
            })
            
            assignment.insert()
            
            return {
                "status": "success",
                "message": _("작업 할당이 성공적으로 생성되었습니다"),
                "assignment_name": assignment.name
            }
            
        except Exception as e:
            frappe.log_error(f"Work assignment creation failed: {str(e)}")
            return {
                "status": "error",
                "message": _("작업 할당 생성에 실패했습니다")
            }
    
    @frappe.whitelist()
    def get_assignment_history(self, limit=10):
        """Get recent assignment history for this area work type"""
        return frappe.get_all("Work Assignment",
            filters={"area_work_type": self.name},
            fields=["name", "assigned_to", "assignment_date", "due_date", "status", "completion_date"],
            order_by="assignment_date desc",
            limit=limit
        )


@frappe.whitelist()
def get_area_work_types_by_area(work_area, active_only=True):
    """Get all work types for a specific work area"""
    filters = {"work_area": work_area}
    if active_only:
        filters["is_active"] = 1
        
    return frappe.get_all("Area Work Type",
        filters=filters,
        fields=["name", "work_type", "work_type_name", "category", "frequency", "priority_level", "is_mandatory"],
        order_by="priority_level desc, work_type_name asc"
    )


@frappe.whitelist()
def get_area_work_types_by_type(work_type, active_only=True):
    """Get all areas for a specific work type"""
    filters = {"work_type": work_type}
    if active_only:
        filters["is_active"] = 1
        
    return frappe.get_all("Area Work Type",
        filters=filters,
        fields=["name", "work_area", "area_name", "work_site", "frequency", "priority_level", "is_mandatory"],
        order_by="priority_level desc, area_name asc"
    )


@frappe.whitelist()
def get_mandatory_work_types_for_area(work_area):
    """Get mandatory work types for a specific area"""
    return frappe.get_all("Area Work Type",
        filters={
            "work_area": work_area,
            "is_active": 1,
            "is_mandatory": 1
        },
        fields=["name", "work_type", "work_type_name", "frequency", "priority_level"],
        order_by="priority_level desc"
    )


@frappe.whitelist()
def get_overdue_assignments_by_frequency():
    """Get areas that have overdue assignments based on frequency"""
    # This would be a complex query to identify areas that haven't had
    # their mandatory work types completed within the required frequency
    
    sql = """
        SELECT 
            awt.work_area,
            awt.area_name,
            awt.work_type,
            awt.work_type_name,
            awt.frequency,
            awt.priority_level,
            MAX(wa.completion_date) as last_completion,
            CASE 
                WHEN awt.frequency = 'Daily' THEN DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                WHEN awt.frequency = 'Weekly' THEN DATE_SUB(CURDATE(), INTERVAL 1 WEEK)
                WHEN awt.frequency = 'Bi-weekly' THEN DATE_SUB(CURDATE(), INTERVAL 2 WEEK)
                WHEN awt.frequency = 'Monthly' THEN DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
                WHEN awt.frequency = 'Quarterly' THEN DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                ELSE NULL
            END as due_date
        FROM `tabArea Work Type` awt
        LEFT JOIN `tabWork Assignment` wa ON wa.area_work_type = awt.name 
            AND wa.status = 'Completed'
        WHERE awt.is_active = 1 
        AND awt.is_mandatory = 1
        AND awt.frequency != 'As Needed'
        GROUP BY awt.name
        HAVING last_completion IS NULL 
        OR last_completion < due_date
        ORDER BY awt.priority_level DESC, due_date ASC
    """
    
    return frappe.db.sql(sql, as_dict=True)


@frappe.whitelist()
def get_area_work_type_summary(area_work_type):
    """Get summary information for an area work type mapping"""
    if not area_work_type:
        return {}
        
    awt_doc = frappe.get_doc("Area Work Type", area_work_type)
    
    # Get assignment statistics
    total_assignments = frappe.db.count("Work Assignment", {"area_work_type": area_work_type})
    completed_assignments = frappe.db.count("Work Assignment", {
        "area_work_type": area_work_type,
        "status": "Completed"
    })
    
    # Get recent assignments
    recent_assignments = frappe.db.count("Work Assignment", {
        "area_work_type": area_work_type,
        "assignment_date": [">=", frappe.utils.add_days(getdate(), -30)]
    })
    
    return {
        "work_area": awt_doc.work_area,
        "area_name": awt_doc.area_name,
        "work_type": awt_doc.work_type,
        "work_type_name": awt_doc.work_type_name,
        "category": awt_doc.category,
        "is_active": awt_doc.is_active,
        "is_mandatory": awt_doc.is_mandatory,
        "frequency": awt_doc.frequency,
        "priority_level": awt_doc.priority_level,
        "formatted_duration": awt_doc.get_formatted_duration(),
        "total_assignments": total_assignments,
        "completed_assignments": completed_assignments,
        "completion_rate": round((completed_assignments / total_assignments * 100), 2) if total_assignments > 0 else 0,
        "recent_assignments": recent_assignments
    }
