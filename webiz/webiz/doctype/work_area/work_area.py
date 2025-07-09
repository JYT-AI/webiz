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


class WorkArea(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and set values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Validate coordinates
        if self.latitude and (self.latitude < -90 or self.latitude > 90):
            frappe.throw(_("위도는 -90과 90 사이여야 합니다"))
            
        if self.longitude and (self.longitude < -180 or self.longitude > 180):
            frappe.throw(_("경도는 -180과 180 사이여야 합니다"))
            
        # Validate area
        if self.area_sqm and self.area_sqm < 0:
            frappe.throw(_("면적은 음수일 수 없습니다"))
            
        # Validate capacity and max workers
        if self.capacity and self.capacity < 0:
            frappe.throw(_("수용 인원은 음수일 수 없습니다"))
            
        if self.max_workers and self.max_workers < 0:
            frappe.throw(_("최대 작업자 수는 음수일 수 없습니다"))
            
        # Validate GPS radius
        if self.gps_radius_meters and self.gps_radius_meters < 0:
            frappe.throw(_("GPS 허용 반경은 음수일 수 없습니다"))
    
    def validate(self):
        """Additional validation"""
        # Check if work site exists
        if self.work_site and not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("사업장 {0}이 존재하지 않습니다").format(self.work_site))
            
        # Check if area code is unique within the work site
        if self.area_code:
            existing = frappe.db.get_value("Work Area", 
                {"work_site": self.work_site, "area_code": self.area_code, "name": ["!=", self.name]}, 
                "name")
            if existing:
                frappe.throw(_("구역 코드 '{0}'은 이미 사업장 '{1}'에서 사용 중입니다").format(
                    self.area_code, self.work_site))
    
    def on_update(self):
        """Actions to perform after update"""
        # Generate QR code if enabled and not exists
        if self.qr_enabled and not self.qr_code:
            self.generate_qr_code()
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_area",
            "transactions": [
                {
                    "label": _("작업 관리"),
                    "items": ["Worker Checkin", "Work Checklist", "Work Assignment"]
                }
            ]
        }
    
    @frappe.whitelist()
    def get_active_workers(self):
        """Get list of workers currently checked in at this area"""
        return frappe.db.sql("""
            SELECT DISTINCT wc.worker, wc.worker_name, wc.checkin_time
            FROM `tabWorker Checkin` wc
            WHERE wc.work_area = %s 
            AND wc.checkin_date = CURDATE()
            AND wc.checkout_time IS NULL
            ORDER BY wc.checkin_time DESC
        """, (self.name,), as_dict=True)
    
    @frappe.whitelist()
    def get_pending_checklists(self):
        """Get pending checklists for this area"""
        return frappe.get_all("Work Checklist",
            filters={
                "work_area": self.name,
                "status": ["in", ["Pending", "In Progress"]]
            },
            fields=["name", "checklist_name", "status", "assigned_to", "due_date"],
            order_by="due_date asc"
        )

    @frappe.whitelist()
    def generate_qr_code(self):
        """Generate QR code for the work area"""
        if not QR_CODE_AVAILABLE:
            return {
                "status": "error",
                "message": _("QR 코드 라이브러리가 설치되지 않았습니다. 'qrcode' 패키지를 설치해주세요.")
            }

        try:
            # Create QR code data (minimal information)
            qr_data = {
                "t": "wac",  # type: work_area_checkin (shortened)
                "wa": self.name,  # work_area (shortened)
                "ws": self.work_site,  # work_site (shortened)
                "ts": int(now().timestamp())  # timestamp (shortened)
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
                "file_name": f"qr_code_area_{self.name}.png",
                "content": img_str,
                "decode": True,
                "is_private": 0,
                "attached_to_doctype": "Work Area",
                "attached_to_name": self.name
            })
            file_doc.insert()

            # Update work area
            self.qr_code = file_doc.file_url
            self.qr_code_data = qr_string
            self.qr_generated_date = now()
            self.save()

            return {
                "status": "success",
                "message": _("QR 코드가 성공적으로 생성되었습니다"),
                "qr_code_url": self.qr_code
            }

        except Exception as e:
            frappe.log_error(f"QR Code generation failed: {str(e)}")
            return {
                "status": "error",
                "message": _("QR 코드 생성에 실패했습니다")
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
def get_area_summary(work_area):
    """Get summary information for a work area"""
    if not work_area:
        return {}
        
    area_doc = frappe.get_doc("Work Area", work_area)
    
    # Get worker count
    worker_count = frappe.db.count("Worker Checkin", {
        "work_area": work_area,
        "checkin_date": getdate(),
        "checkout_time": ["is", "not set"]
    })
    
    # Get pending tasks
    pending_tasks = frappe.db.count("Work Checklist", {
        "work_area": work_area,
        "status": ["in", ["Pending", "In Progress"]]
    })
    
    # Get completed tasks today
    completed_today = frappe.db.count("Work Checklist", {
        "work_area": work_area,
        "status": "Completed",
        "completion_date": getdate()
    })
    
    return {
        "area_name": area_doc.area_name,
        "status": area_doc.status,
        "work_site": area_doc.work_site,
        "site_name": area_doc.site_name,
        "area_manager": area_doc.area_manager,
        "active_workers": worker_count,
        "pending_tasks": pending_tasks,
        "completed_today": completed_today,
        "area_type": area_doc.area_type,
        "floor_level": area_doc.floor_level
    }


@frappe.whitelist()
def get_areas_by_site(work_site):
    """Get all work areas for a specific work site"""
    if not work_site:
        return []
        
    return frappe.get_all("Work Area",
        filters={"work_site": work_site, "status": "Active"},
        fields=["name", "area_name", "area_code", "area_type", "floor_level", "status"],
        order_by="area_name asc"
    )
