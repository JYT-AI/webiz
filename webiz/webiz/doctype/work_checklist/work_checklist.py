# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt
from frappe import _


class WorkChecklist(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and calculate values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Calculate progress and scores
        self.calculate_progress()
        self.calculate_scores()
        
        # Update status based on completion
        self.update_status_based_on_progress()
        
        # Validate dates
        if self.start_date and self.due_date:
            if getdate(self.start_date) > getdate(self.due_date):
                frappe.throw(_("Start Date cannot be after Due Date"))
    
    def calculate_progress(self):
        """Calculate completion percentage and item counts"""
        if not self.checklist_items:
            self.total_items = 0
            self.completed_items = 0
            self.completion_percentage = 0
            return
        
        total_items = len(self.checklist_items)
        completed_items = len([item for item in self.checklist_items if item.is_completed])
        
        self.total_items = total_items
        self.completed_items = completed_items
        self.completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    def calculate_scores(self):
        """Calculate total and achieved scores"""
        if not self.checklist_items:
            self.total_score = 0
            self.achieved_score = 0
            return
        
        total_score = sum([flt(item.max_score) for item in self.checklist_items])
        achieved_score = sum([flt(item.score) for item in self.checklist_items if item.is_completed])
        
        self.total_score = total_score
        self.achieved_score = achieved_score
    
    def update_status_based_on_progress(self):
        """Update status based on completion percentage"""
        if self.completion_percentage == 100:
            if self.status != "Completed":
                self.status = "Completed"
                self.completion_date = getdate()
        elif self.completion_percentage > 0:
            if self.status == "Pending":
                self.status = "In Progress"
    
    def validate(self):
        """Additional validation"""
        # Check if work site exists
        if not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("Work Site {0} does not exist").format(self.work_site))
        
        # Check if assigned employee exists
        if not frappe.db.exists("Employee", self.assigned_to):
            frappe.throw(_("Employee {0} does not exist").format(self.assigned_to))
        
        # Validate project belongs to work site customer if both are specified
        if self.project and self.work_site:
            work_site_customer = frappe.db.get_value("Work Site", self.work_site, "customer")
            project_customer = frappe.db.get_value("Project", self.project, "customer")
            
            if work_site_customer and project_customer and work_site_customer != project_customer:
                frappe.throw(_("Project {0} does not belong to the same customer as Work Site {1}").format(
                    self.project, self.work_site))
    
    @frappe.whitelist()
    def mark_item_completed(self, item_idx, completed_by=None, score=None, notes=None, photo=None):
        """Mark a specific checklist item as completed"""
        if item_idx >= len(self.checklist_items):
            frappe.throw(_("Invalid item index"))
        
        item = self.checklist_items[item_idx]
        item.is_completed = 1
        item.completion_date = now()
        item.completed_by = completed_by or frappe.session.user
        
        if score is not None:
            item.score = flt(score)
        else:
            item.score = item.max_score  # Default to max score
        
        if notes:
            item.notes = notes
        if photo:
            item.photo = photo
        
        # Recalculate progress
        self.calculate_progress()
        self.calculate_scores()
        self.update_status_based_on_progress()
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Item marked as completed"),
            "completion_percentage": self.completion_percentage
        }
    
    @frappe.whitelist()
    def mark_item_incomplete(self, item_idx):
        """Mark a specific checklist item as incomplete"""
        if item_idx >= len(self.checklist_items):
            frappe.throw(_("Invalid item index"))
        
        item = self.checklist_items[item_idx]
        item.is_completed = 0
        item.completion_date = None
        item.completed_by = None
        item.score = 0
        
        # Recalculate progress
        self.calculate_progress()
        self.calculate_scores()
        
        # Update status if needed
        if self.completion_percentage < 100 and self.status == "Completed":
            self.status = "In Progress" if self.completion_percentage > 0 else "Pending"
            self.completion_date = None
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Item marked as incomplete"),
            "completion_percentage": self.completion_percentage
        }
    
    @frappe.whitelist()
    def complete_checklist(self, supervisor_comments=None, quality_rating=None):
        """Complete the entire checklist"""
        # Check if all mandatory items are completed
        mandatory_items = [item for item in self.checklist_items if item.is_mandatory]
        incomplete_mandatory = [item for item in mandatory_items if not item.is_completed]
        
        if incomplete_mandatory:
            frappe.throw(_("Cannot complete checklist. The following mandatory items are not completed: {0}").format(
                ", ".join([item.item_name for item in incomplete_mandatory])))
        
        self.status = "Completed"
        self.completion_date = getdate()
        
        if supervisor_comments:
            self.supervisor_comments = supervisor_comments
        if quality_rating:
            self.quality_rating = quality_rating
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Checklist completed successfully"),
            "completion_date": self.completion_date
        }
    
    @frappe.whitelist()
    def get_progress_summary(self):
        """Get detailed progress summary"""
        summary = {
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "completion_percentage": self.completion_percentage,
            "total_score": self.total_score,
            "achieved_score": self.achieved_score,
            "quality_rating": self.quality_rating,
            "status": self.status
        }
        
        # Item breakdown by type
        item_types = {}
        for item in self.checklist_items:
            item_type = item.item_type
            if item_type not in item_types:
                item_types[item_type] = {"total": 0, "completed": 0}
            
            item_types[item_type]["total"] += 1
            if item.is_completed:
                item_types[item_type]["completed"] += 1
        
        summary["item_types"] = item_types
        
        return summary
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_checklist",
            "transactions": [
                {
                    "label": _("Work Management"),
                    "items": ["Work Report", "Worker Checkin"]
                },
                {
                    "label": _("Project Management"),
                    "items": ["Task", "Timesheet"]
                }
            ]
        }


@frappe.whitelist()
def create_checklist_from_template(template_name, work_site, assigned_to, due_date=None):
    """Create a new checklist from a template"""
    # This function would create checklists from predefined templates
    # For now, we'll create a basic template
    
    basic_items = [
        {"item_name": "Safety Equipment Check", "item_type": "Safety Check", "is_mandatory": 1, "max_score": 10},
        {"item_name": "Work Area Preparation", "item_type": "Task", "is_mandatory": 1, "max_score": 10},
        {"item_name": "Quality Inspection", "item_type": "Quality Check", "is_mandatory": 1, "max_score": 15},
        {"item_name": "Clean Up", "item_type": "Cleaning", "is_mandatory": 0, "max_score": 5},
        {"item_name": "Documentation", "item_type": "Documentation", "is_mandatory": 1, "max_score": 10}
    ]
    
    checklist = frappe.get_doc({
        "doctype": "Work Checklist",
        "checklist_name": f"{template_name} - {work_site}",
        "work_site": work_site,
        "assigned_to": assigned_to,
        "due_date": due_date,
        "checklist_type": template_name,
        "status": "Pending"
    })
    
    for item_data in basic_items:
        checklist.append("checklist_items", item_data)
    
    checklist.insert()
    
    return checklist.name


@frappe.whitelist()
def get_checklist_templates():
    """Get available checklist templates"""
    return [
        {"name": "Daily", "description": "Daily routine checklist"},
        {"name": "Safety", "description": "Safety inspection checklist"},
        {"name": "Quality", "description": "Quality control checklist"},
        {"name": "Maintenance", "description": "Equipment maintenance checklist"},
        {"name": "Inspection", "description": "General inspection checklist"}
    ]
