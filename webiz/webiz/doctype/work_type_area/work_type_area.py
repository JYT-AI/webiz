# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkTypeArea(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        area_type: DF.Literal["Office", "Warehouse", "Production", "Maintenance", "Storage", "Common Area", "Restroom", "Kitchen", "Meeting Room", "Other"]
        estimated_frequency: DF.Literal["Daily", "Weekly", "Bi-weekly", "Monthly", "Quarterly", "As Needed"]
        is_mandatory: DF.Check
        notes: DF.SmallText | None
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
    # end: auto-generated types

    pass
