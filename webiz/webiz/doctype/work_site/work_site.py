# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt
from frappe import _
import io
import base64
import json

# Optional QR code import
try:
    import qrcode
    QR_CODE_AVAILABLE = True
except ImportError:
    QR_CODE_AVAILABLE = False


class WorkSite(Document):
    def before_insert(self):
        """Set default values before inserting"""
        # 단순화된 시스템에서는 기본 설정만 수행
        pass
        
    def before_save(self):
        """Validate and set values before saving"""
        # 단순화된 검증만 수행
        pass
    
    def validate(self):
        """Additional validation"""
        # Check if customer exists
        if self.customer and not frappe.db.exists("Customer", self.customer):
            frappe.throw(_("Customer {0} does not exist").format(self.customer))
    
    def on_update(self):
        """Actions to perform after update"""
        # Generate QR code if enabled and not exists
        if self.qr_enabled and not self.qr_code:
            self.generate_qr_code()
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_site",
            "transactions": [
                {
                    "label": _("Work Management"),
                    "items": ["Worker Checkin", "Work Checklist", "Work Report"]
                },
                {
                    "label": _("Project Management"),
                    "items": ["Task", "Timesheet"]
                }
            ]
        }
    
    @frappe.whitelist()
    def get_location_info(self):
        """Get formatted location information"""
        return self.address or ""
    
    @frappe.whitelist()
    def get_active_workers(self):
        """Get list of workers currently checked in at this site"""
        return frappe.db.sql("""
            SELECT DISTINCT wc.worker, wc.worker_name, wc.checkin_time
            FROM `tabWorker Checkin` wc
            WHERE wc.work_site = %s 
            AND wc.checkin_date = CURDATE()
            AND wc.checkout_time IS NULL
            ORDER BY wc.checkin_time DESC
        """, (self.name,), as_dict=True)
    
    @frappe.whitelist()
    def get_pending_checklists(self):
        """Get pending checklists for this site"""
        return frappe.get_all("Work Checklist",
            filters={
                "work_site": self.name,
                "status": ["in", ["Pending", "In Progress"]]
            },
            fields=["name", "checklist_name", "status", "assigned_to", "due_date"],
            order_by="due_date asc"
        )

    @frappe.whitelist()
    def generate_qr_code(self):
        """Generate QR code for the work site"""
        if not QR_CODE_AVAILABLE:
            return {
                "status": "error",
                "message": _("QR Code library not installed. Please install 'qrcode' package.")
            }

        try:
            # Create QR code data (minimal information)
            qr_data = {
                "type": "work_site_checkin",
                "work_location": self.name,
                "timestamp": int(now().timestamp())
            }

            # Convert to JSON string
            qr_string = json.dumps(qr_data)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)

            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            # Save as file
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": f"qr_code_{self.name}.png",
                "content": img_str,
                "decode": True,
                "is_private": 0,
                "attached_to_doctype": "Work Site",
                "attached_to_name": self.name
            })
            file_doc.insert()

            # Update work site
            self.qr_code = file_doc.file_url
            self.qr_code_data = qr_string
            self.qr_generated_date = now()
            self.save()

            return {
                "status": "success",
                "message": _("QR Code generated successfully"),
                "qr_code_url": self.qr_code
            }

        except Exception as e:
            frappe.log_error(f"QR Code generation failed: {str(e)}")
            return {
                "status": "error",
                "message": _("Failed to generate QR Code")
            }

    @frappe.whitelist()
    def regenerate_qr_code(self):
        """Regenerate QR code"""
        # Delete old QR code file if exists
        if self.qr_code:
            try:
                old_file = frappe.get_doc("File", {"file_url": self.qr_code})
                old_file.delete()
            except:
                pass

        # Clear QR code fields
        self.qr_code = None
        self.qr_code_data = None
        self.qr_generated_date = None

        # Generate new QR code
        return self.generate_qr_code()


@frappe.whitelist()
def get_site_summary(work_site):
    """Get summary information for a work site"""
    if not work_site:
        return {}
        
    site_doc = frappe.get_doc("Work Site", work_site)
    
    # Get worker count
    worker_count = frappe.db.count("Worker Checkin", {
        "work_site": work_site,
        "checkin_date": getdate(),
        "checkout_time": ["is", "not set"]
    })
    
    # Get pending tasks
    pending_tasks = frappe.db.count("Work Checklist", {
        "work_site": work_site,
        "status": ["in", ["Pending", "In Progress"]]
    })
    
    # Get completed tasks today
    completed_today = frappe.db.count("Work Checklist", {
        "work_site": work_site,
        "status": "Completed",
        "completion_date": getdate()
    })
    
    return {
        "site_name": site_doc.site_name,
        "status": site_doc.status,
        "customer": site_doc.customer,
        "active_workers": worker_count,
        "pending_tasks": pending_tasks,
        "completed_today": completed_today,
        "location": site_doc.get_location_info()
    }


@frappe.whitelist()
def get_nearby_sites(latitude=None, longitude=None, radius_km=10):
    """Get work sites within specified radius - simplified version"""
    # 단순화된 시스템에서는 GPS 좌표를 사용하지 않으므로 모든 활성 사이트 반환
    sites = frappe.get_all("Work Site",
        filters={"status": "Active"},
        fields=["name", "site_name", "customer", "address"],
        order_by="site_name"
    )

    return sites
