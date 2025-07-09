# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, flt
from frappe import _


class WorkChecklistItem(Document):
    def before_save(self):
        """Validate and set values before saving"""
        # Validate score
        if self.score and self.max_score:
            if flt(self.score) > flt(self.max_score):
                frappe.throw(_("Score cannot be greater than Max Score"))
        
        # Set completion date when marked as completed
        if self.is_completed and not self.completion_date:
            self.completion_date = now()
            if not self.completed_by:
                self.completed_by = frappe.session.user
        
        # Clear completion data when marked as incomplete
        if not self.is_completed:
            self.completion_date = None
            self.completed_by = None
            self.score = 0
    
    def validate(self):
        """Additional validation"""
        # Validate max score
        if self.max_score and flt(self.max_score) <= 0:
            frappe.throw(_("Max Score must be greater than 0"))
        
        # Validate score
        if self.score and flt(self.score) < 0:
            frappe.throw(_("Score cannot be negative"))
    
    @frappe.whitelist()
    def mark_completed(self, score=None, notes=None, photo=None, completed_by=None):
        """Mark this item as completed"""
        self.is_completed = 1
        self.completion_date = now()
        self.completed_by = completed_by or frappe.session.user
        
        if score is not None:
            self.score = flt(score)
        else:
            self.score = self.max_score  # Default to max score
        
        if notes:
            self.notes = notes
        if photo:
            self.photo = photo
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Item marked as completed"),
            "completion_date": self.completion_date,
            "score": self.score
        }
    
    @frappe.whitelist()
    def mark_incomplete(self):
        """Mark this item as incomplete"""
        self.is_completed = 0
        self.completion_date = None
        self.completed_by = None
        self.score = 0
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Item marked as incomplete")
        }
    
    def get_completion_status(self):
        """Get formatted completion status"""
        if self.is_completed:
            return {
                "status": "Completed",
                "completion_date": self.completion_date,
                "completed_by": self.completed_by,
                "score": self.score,
                "max_score": self.max_score,
                "score_percentage": (flt(self.score) / flt(self.max_score) * 100) if self.max_score else 0
            }
        else:
            return {
                "status": "Pending",
                "completion_date": None,
                "completed_by": None,
                "score": 0,
                "max_score": self.max_score,
                "score_percentage": 0
            }
