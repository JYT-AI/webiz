# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ChecklistTemplateItem(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        description: DF.Text | None
        is_mandatory: DF.Check
        item_name: DF.Data
        item_type: DF.Literal["Task", "Safety Check", "Quality Check", "Cleaning", "Inspection", "Maintenance", "Documentation", "Other"]
        max_score: DF.Float
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        reference_document: DF.Data | None
        reference_link: DF.Data | None
        requires_note: DF.Check
        requires_photo: DF.Check
        safety_note: DF.SmallText | None
        sequence: DF.Int | None
        special_instructions: DF.SmallText | None
    # end: auto-generated types

    pass
