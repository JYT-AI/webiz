# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _


class WorkInstructionStep(Document):
    def validate(self):
        """Validation for work instruction step"""
        # Validate step number
        if self.step_number and self.step_number <= 0:
            frappe.throw(_("Step number must be greater than 0"))
        
        # Validate estimated duration
        if self.estimated_duration and self.estimated_duration < 0:
            frappe.throw(_("Estimated duration cannot be negative"))
    
    def get_formatted_step(self):
        """Get formatted step information for display"""
        return {
            "number": self.step_number,
            "title": self.step_title,
            "type": self.step_type,
            "is_critical": self.is_critical,
            "description": self.step_description,
            "procedure": self.detailed_procedure,
            "safety": self.safety_note,
            "warning": self.warning_message,
            "duration": self.estimated_duration,
            "tools": self.required_tools_step,
            "image": self.step_image,
            "video": self.reference_video,
            "verification": self.verification_method,
            "criteria": self.acceptance_criteria
        }
