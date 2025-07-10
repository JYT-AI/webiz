# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, add_days
from frappe import _


class WorkInstruction(Document):
    # Website configuration for web view functionality
    website = frappe._dict(
        condition_field="status",  # Field to check for publishing condition
        page_title_field="instruction_title"  # Field to use as page title
    )

    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and set values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Validate dates
        if self.effective_date and self.expiry_date:
            if getdate(self.effective_date) > getdate(self.expiry_date):
                frappe.throw(_("Effective Date cannot be after Expiry Date"))
        
        # Auto-set effective date if approved
        if self.status == "Approved" and not self.effective_date:
            self.effective_date = getdate()
        
        # Update revision history
        if self.has_value_changed("status") or self.has_value_changed("version"):
            self.update_revision_history()
    
    def validate(self):
        """Additional validation"""
        # Check if work site exists
        if self.work_site and not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("Work Site {0} does not exist").format(self.work_site))
        
        # Validate step numbers are sequential
        if self.step_by_step_guide:
            step_numbers = [step.step_number for step in self.step_by_step_guide]
            if len(step_numbers) != len(set(step_numbers)):
                frappe.throw(_("Step numbers must be unique"))
            
            expected_numbers = list(range(1, len(step_numbers) + 1))
            if sorted(step_numbers) != expected_numbers:
                frappe.throw(_("Step numbers must be sequential starting from 1"))
    
    def update_revision_history(self):
        """Update revision history"""
        history_entry = f"{now()}: Status changed to {self.status}"
        if self.has_value_changed("version"):
            history_entry += f", Version updated to {self.version}"
        history_entry += f" by {frappe.session.user}\n"
        
        if self.revision_history:
            self.revision_history += history_entry
        else:
            self.revision_history = history_entry
    
    def on_update(self):
        """Actions to perform after update"""
        # Send notifications if enabled
        if self.send_notifications and self.has_value_changed("status"):
            self.send_status_notifications()
        
        # Auto-assign to checklists if enabled
        if self.auto_assign_checklist and self.status == "Active":
            self.assign_to_checklists()
    
    def send_status_notifications(self):
        """Send notifications about status change"""
        if not self.notification_list:
            return
        
        emails = [email.strip() for email in self.notification_list.split(',') if email.strip()]
        if not emails:
            return
        
        subject = f"Work Instruction Update: {self.instruction_title}"
        message = f"""
        Work Instruction has been updated:
        
        Title: {self.instruction_title}
        Status: {self.status}
        Version: {self.version}
        Work Site: {self.work_site or 'General'}
        
        {self.instruction_summary or ''}
        
        Please review the updated instruction in the system.
        """
        
        frappe.sendmail(
            recipients=emails,
            subject=subject,
            message=message
        )
    
    def assign_to_checklists(self):
        """Auto-assign instruction to related checklists"""
        if not self.related_checklists:
            return
        
        for checklist_ref in self.related_checklists:
            try:
                checklist = frappe.get_doc("Work Checklist", checklist_ref.work_checklist)
                
                # Add instruction reference to checklist
                if not checklist.instructions:
                    checklist.instructions = self.name
                elif self.name not in checklist.instructions:
                    checklist.instructions += f", {self.name}"
                
                checklist.save()
            except Exception as e:
                frappe.log_error(f"Failed to assign instruction to checklist: {str(e)}")
    
    @frappe.whitelist()
    def approve_instruction(self, approved_by=None):
        """Approve the instruction"""
        if self.status != "Under Review":
            frappe.throw(_("Only instructions under review can be approved"))
        
        self.status = "Approved"
        self.approved_by = approved_by or frappe.session.user
        self.approval_date = getdate()
        
        # Auto-activate if no effective date is set
        if not self.effective_date:
            self.effective_date = getdate()
            self.status = "Active"
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Instruction approved successfully")
        }
    
    @frappe.whitelist()
    def activate_instruction(self):
        """Activate the instruction"""
        if self.status != "Approved":
            frappe.throw(_("Only approved instructions can be activated"))
        
        if self.effective_date and getdate(self.effective_date) > getdate():
            frappe.throw(_("Cannot activate instruction before effective date"))
        
        self.status = "Active"
        self.save()
        
        return {
            "status": "success",
            "message": _("Instruction activated successfully")
        }
    
    @frappe.whitelist()
    def create_new_version(self, version_notes=None):
        """Create a new version of the instruction"""
        # Parse current version and increment
        try:
            current_version = float(self.version)
            new_version = str(current_version + 0.1)
        except:
            new_version = "2.0"
        
        # Create new instruction document
        new_instruction = frappe.copy_doc(self)
        new_instruction.version = new_version
        new_instruction.status = "Draft"
        new_instruction.approved_by = None
        new_instruction.approval_date = None
        new_instruction.effective_date = None
        new_instruction.revision_history = f"Created from version {self.version}\n"
        
        if version_notes:
            new_instruction.revision_history += f"Notes: {version_notes}\n"
        
        new_instruction.insert()
        
        # Deactivate current version
        self.status = "Inactive"
        self.save()
        
        return {
            "status": "success",
            "message": _("New version {0} created").format(new_version),
            "new_version": new_instruction.name
        }
    
    @frappe.whitelist()
    def get_instruction_for_mobile(self):
        """Get instruction formatted for mobile display"""
        steps = []
        for step in self.step_by_step_guide:
            steps.append({
                "step_number": step.step_number,
                "title": step.step_title,
                "description": step.step_description,
                "type": step.step_type,
                "is_critical": step.is_critical,
                "safety_note": step.safety_note,
                "warning": step.warning_message,
                "duration": step.estimated_duration,
                "tools": step.required_tools_step,
                "image": step.step_image,
                "verification": step.verification_method,
                "criteria": step.acceptance_criteria
            })
        
        return {
            "instruction": {
                "title": self.instruction_title,
                "summary": self.instruction_summary,
                "type": self.instruction_type,
                "priority": self.priority,
                "estimated_time": self.estimated_time,
                "safety_requirements": self.safety_requirements,
                "required_tools": self.required_tools,
                "required_materials": self.required_materials,
                "skill_level": self.skill_level_required,
                "certification": self.certification_required
            },
            "steps": steps
        }
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_instruction",
            "transactions": [
                {
                    "label": _("Site Management"),
                    "items": ["Work Checklist", "Work Report"]
                },
                {
                    "label": _("Training"),
                    "items": ["Training Program", "Training Record"]
                }
            ]
        }


@frappe.whitelist()
def get_instructions_for_site(work_site, instruction_type=None, active_only=True):
    """Get work instructions for a specific site"""
    filters = {"work_site": work_site}
    
    if instruction_type:
        filters["instruction_type"] = instruction_type
    
    if active_only:
        filters["status"] = "Active"
    
    instructions = frappe.get_all("Work Instruction",
        filters=filters,
        fields=[
            "name", "instruction_title", "instruction_type", "priority",
            "instruction_summary", "estimated_time", "skill_level_required"
        ],
        order_by="priority desc, instruction_title asc"
    )
    
    return instructions


@frappe.whitelist()
def search_instructions(query, work_site=None, instruction_type=None):
    """Search work instructions"""
    conditions = ["status = 'Active'"]
    values = []
    
    if work_site:
        conditions.append("work_site = %s")
        values.append(work_site)
    
    if instruction_type:
        conditions.append("instruction_type = %s")
        values.append(instruction_type)
    
    if query:
        conditions.append("(instruction_title LIKE %s OR instruction_summary LIKE %s)")
        values.extend([f"%{query}%", f"%{query}%"])
    
    sql = f"""
        SELECT name, instruction_title, instruction_type, priority, instruction_summary
        FROM `tabWork Instruction`
        WHERE {' AND '.join(conditions)}
        ORDER BY priority DESC, instruction_title ASC
        LIMIT 20
    """
    
    return frappe.db.sql(sql, values, as_dict=True)
