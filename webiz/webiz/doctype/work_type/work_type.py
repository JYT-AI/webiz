# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt
from frappe import _


class WorkType(Document):
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
    
    def validate(self):
        """Additional validation"""
        # Check if work type code is unique
        if self.work_type_code:
            existing = frappe.db.get_value("Work Type", 
                {"work_type_code": self.work_type_code, "name": ["!=", self.name]}, 
                "name")
            if existing:
                frappe.throw(_("업무유형 코드 '{0}'은 이미 사용 중입니다").format(self.work_type_code))
                
        # Validate checklist template exists
        if self.default_checklist_template and not frappe.db.exists("Checklist Template", self.default_checklist_template):
            frappe.throw(_("체크리스트 템플릿 '{0}'이 존재하지 않습니다").format(self.default_checklist_template))
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_type",
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
    def get_applicable_area_types(self):
        """Get list of applicable area types"""
        area_types = []
        for area in self.applicable_areas:
            area_types.append({
                "area_type": area.area_type,
                "is_mandatory": area.is_mandatory,
                "estimated_frequency": area.estimated_frequency,
                "notes": area.notes
            })
        return area_types
    
    @frappe.whitelist()
    def create_checklist_from_template(self, work_area, assigned_to, due_date=None):
        """Create a work checklist from the default template"""
        if not self.default_checklist_template:
            return {
                "status": "error",
                "message": _("이 업무유형에는 기본 체크리스트 템플릿이 설정되지 않았습니다")
            }
        
        try:
            # Get template
            template = frappe.get_doc("Checklist Template", self.default_checklist_template)
            
            # Create checklist
            checklist = frappe.get_doc({
                "doctype": "Work Checklist",
                "checklist_name": f"{self.work_type_name} - {work_area}",
                "work_area": work_area,
                "work_type": self.name,
                "assigned_to": assigned_to,
                "due_date": due_date or getdate(),
                "checklist_type": self.work_type_name,
                "status": "Pending",
                "description": template.description,
                "instructions": template.instructions
            })
            
            # Copy template items
            for template_item in template.template_items:
                checklist.append("checklist_items", {
                    "item_name": template_item.item_name,
                    "description": template_item.description,
                    "item_type": template_item.item_type,
                    "is_mandatory": template_item.is_mandatory,
                    "max_score": template_item.max_score,
                    "is_completed": 0
                })
            
            checklist.insert()
            
            return {
                "status": "success",
                "message": _("체크리스트가 성공적으로 생성되었습니다"),
                "checklist_name": checklist.name
            }
            
        except Exception as e:
            frappe.log_error(f"Checklist creation failed: {str(e)}")
            return {
                "status": "error",
                "message": _("체크리스트 생성에 실패했습니다")
            }


@frappe.whitelist()
def get_work_types_by_category(category=None):
    """Get work types filtered by category"""
    filters = {"status": "Active"}
    if category:
        filters["category"] = category
        
    return frappe.get_all("Work Type",
        filters=filters,
        fields=["name", "work_type_name", "work_type_code", "category", "difficulty_level", "estimated_duration_hours", "estimated_duration_minutes"],
        order_by="work_type_name asc"
    )


@frappe.whitelist()
def get_work_types_for_area_type(area_type):
    """Get work types applicable for a specific area type"""
    if not area_type:
        return []
    
    # Get work types that have this area type in their applicable areas
    work_types = frappe.db.sql("""
        SELECT DISTINCT wt.name, wt.work_type_name, wt.work_type_code, wt.category,
               wt.difficulty_level, wt.estimated_duration_hours, wt.estimated_duration_minutes,
               wta.is_mandatory, wta.estimated_frequency
        FROM `tabWork Type` wt
        LEFT JOIN `tabWork Type Area` wta ON wta.parent = wt.name
        WHERE wt.status = 'Active'
        AND (wta.area_type = %s OR wta.area_type IS NULL)
        ORDER BY wt.work_type_name
    """, (area_type,), as_dict=True)
    
    return work_types


@frappe.whitelist()
def get_work_type_summary(work_type):
    """Get summary information for a work type"""
    if not work_type:
        return {}
        
    work_type_doc = frappe.get_doc("Work Type", work_type)
    
    # Get usage statistics
    total_assignments = frappe.db.count("Work Assignment", {"work_type": work_type})
    completed_assignments = frappe.db.count("Work Assignment", {
        "work_type": work_type,
        "status": "Completed"
    })
    
    # Get recent checklists
    recent_checklists = frappe.db.count("Work Checklist", {
        "work_type": work_type,
        "creation": [">=", frappe.utils.add_days(getdate(), -30)]
    })
    
    return {
        "work_type_name": work_type_doc.work_type_name,
        "category": work_type_doc.category,
        "status": work_type_doc.status,
        "difficulty_level": work_type_doc.difficulty_level,
        "formatted_duration": work_type_doc.get_formatted_duration(),
        "total_assignments": total_assignments,
        "completed_assignments": completed_assignments,
        "completion_rate": round((completed_assignments / total_assignments * 100), 2) if total_assignments > 0 else 0,
        "recent_checklists": recent_checklists,
        "applicable_areas": len(work_type_doc.applicable_areas)
    }
