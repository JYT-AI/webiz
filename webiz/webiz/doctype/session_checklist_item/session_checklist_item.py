# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class SessionChecklistItem(Document):
    def before_save(self):
        """Set completion time when item is completed"""
        if self.is_completed and not self.completion_time:
            self.completion_time = now()
        elif not self.is_completed:
            self.completion_time = None
