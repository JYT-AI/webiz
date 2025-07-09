# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt
from frappe import _


class ChecklistTemplate(Document):
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
            
        # Calculate summary fields
        self.calculate_summary_fields()
    
    def validate(self):
        """Additional validation"""
        # Check if template code is unique
        if self.template_code:
            existing = frappe.db.get_value("Checklist Template", 
                {"template_code": self.template_code, "name": ["!=", self.name]}, 
                "name")
            if existing:
                frappe.throw(_("템플릿 코드 '{0}'은 이미 사용 중입니다").format(self.template_code))
                
        # Validate work type exists
        if self.work_type and not frappe.db.exists("Work Type", self.work_type):
            frappe.throw(_("업무유형 '{0}'이 존재하지 않습니다").format(self.work_type))
            
        # Validate template items
        if not self.template_items:
            frappe.throw(_("최소 하나의 템플릿 항목이 필요합니다"))
            
        # Check for duplicate item names
        item_names = []
        for item in self.template_items:
            if item.item_name in item_names:
                frappe.throw(_("중복된 항목명이 있습니다: {0}").format(item.item_name))
            item_names.append(item.item_name)
    
    def calculate_summary_fields(self):
        """Calculate summary fields from template items"""
        self.total_items = len(self.template_items)
        self.mandatory_items = sum(1 for item in self.template_items if item.is_mandatory)
        self.total_max_score = sum(flt(item.max_score) for item in self.template_items)
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "checklist_template",
            "transactions": [
                {
                    "label": _("작업 관리"),
                    "items": ["Work Checklist", "Work Type"]
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
    def create_checklist(self, work_area, assigned_to, due_date=None, work_site=None):
        """Create a work checklist from this template"""
        try:
            # Create checklist
            checklist = frappe.get_doc({
                "doctype": "Work Checklist",
                "checklist_name": f"{self.template_name} - {work_area}",
                "work_area": work_area,
                "work_site": work_site,
                "checklist_template": self.name,
                "assigned_to": assigned_to,
                "due_date": due_date or getdate(),
                "checklist_type": self.category,
                "status": "Pending",
                "description": self.description,
                "instructions": self.instructions,
                "estimated_hours": self.get_total_duration_minutes() / 60 if self.get_total_duration_minutes() else None
            })
            
            # Copy template items
            for template_item in self.template_items:
                checklist.append("checklist_items", {
                    "item_name": template_item.item_name,
                    "description": template_item.description,
                    "item_type": template_item.item_type,
                    "is_mandatory": template_item.is_mandatory,
                    "max_score": template_item.max_score,
                    "is_completed": 0,
                    "reference_document": template_item.reference_document,
                    "reference_link": template_item.reference_link
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
    def duplicate_template(self, new_name, new_code=None):
        """Create a duplicate of this template"""
        try:
            # Create new template
            new_template = frappe.copy_doc(self)
            new_template.template_name = new_name
            new_template.template_code = new_code
            new_template.status = "Draft"
            new_template.version = "1.0"
            new_template.revision_notes = f"복사본 생성 (원본: {self.name})"
            
            new_template.insert()
            
            return {
                "status": "success",
                "message": _("템플릿이 성공적으로 복사되었습니다"),
                "template_name": new_template.name
            }
            
        except Exception as e:
            frappe.log_error(f"Template duplication failed: {str(e)}")
            return {
                "status": "error",
                "message": _("템플릿 복사에 실패했습니다")
            }
    
    @frappe.whitelist()
    def get_usage_statistics(self):
        """Get usage statistics for this template"""
        # Get total checklists created from this template
        total_checklists = frappe.db.count("Work Checklist", {"checklist_template": self.name})
        
        # Get completed checklists
        completed_checklists = frappe.db.count("Work Checklist", {
            "checklist_template": self.name,
            "status": "Completed"
        })
        
        # Get recent usage (last 30 days)
        recent_usage = frappe.db.count("Work Checklist", {
            "checklist_template": self.name,
            "creation": [">=", frappe.utils.add_days(getdate(), -30)]
        })
        
        # Get average completion time
        avg_completion_time = frappe.db.sql("""
            SELECT AVG(TIMESTAMPDIFF(HOUR, start_date, completion_date)) as avg_hours
            FROM `tabWork Checklist`
            WHERE checklist_template = %s
            AND status = 'Completed'
            AND start_date IS NOT NULL
            AND completion_date IS NOT NULL
        """, (self.name,), as_dict=True)
        
        avg_hours = avg_completion_time[0].avg_hours if avg_completion_time and avg_completion_time[0].avg_hours else 0
        
        return {
            "total_checklists": total_checklists,
            "completed_checklists": completed_checklists,
            "completion_rate": round((completed_checklists / total_checklists * 100), 2) if total_checklists > 0 else 0,
            "recent_usage": recent_usage,
            "avg_completion_hours": round(avg_hours, 2) if avg_hours else 0
        }


@frappe.whitelist()
def get_templates_by_category(category=None):
    """Get checklist templates filtered by category"""
    filters = {"status": "Active"}
    if category:
        filters["category"] = category
        
    return frappe.get_all("Checklist Template",
        filters=filters,
        fields=["name", "template_name", "template_code", "category", "difficulty_level", "total_items", "total_max_score"],
        order_by="template_name asc"
    )


@frappe.whitelist()
def get_templates_for_work_type(work_type):
    """Get checklist templates for a specific work type"""
    if not work_type:
        return []
        
    return frappe.get_all("Checklist Template",
        filters={"work_type": work_type, "status": "Active"},
        fields=["name", "template_name", "template_code", "category", "difficulty_level", "total_items"],
        order_by="template_name asc"
    )


@frappe.whitelist()
def get_template_summary(template):
    """Get summary information for a checklist template"""
    if not template:
        return {}
        
    template_doc = frappe.get_doc("Checklist Template", template)
    usage_stats = template_doc.get_usage_statistics()
    
    return {
        "template_name": template_doc.template_name,
        "category": template_doc.category,
        "status": template_doc.status,
        "difficulty_level": template_doc.difficulty_level,
        "formatted_duration": template_doc.get_formatted_duration(),
        "total_items": template_doc.total_items,
        "mandatory_items": template_doc.mandatory_items,
        "total_max_score": template_doc.total_max_score,
        **usage_stats
    }
