# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkSiteTemplate(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        category: DF.Data | None
        estimated_minutes: DF.Int | None
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        template_name: DF.Data | None
        work_template: DF.Link | None
    # end: auto-generated types

    pass
