# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, get_time, time_diff_in_hours, flt
from frappe import _
import json


class WorkerCheckin(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
        # Set device and IP information
        if frappe.request:
            self.ip_address = frappe.local.request_ip
            user_agent = frappe.request.headers.get('User-Agent', '')
            self.device_info = user_agent[:100] if user_agent else ''
    
    def before_save(self):
        """Validate and calculate values before saving"""
        # Validate worker exists
        if not frappe.db.exists("Employee", self.worker):
            frappe.throw(_("Employee {0} does not exist").format(self.worker))
        
        # Validate work site exists
        if not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("Work Site {0} does not exist").format(self.work_site))
        
        # Check for duplicate checkin on same date
        if self.is_new():
            existing = frappe.db.exists("Worker Checkin", {
                "worker": self.worker,
                "work_site": self.work_site,
                "checkin_date": self.checkin_date,
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw(_("Worker {0} already has a check-in record for {1} at {2}").format(
                    self.worker_name, self.checkin_date, self.work_site))
        
        # Calculate work hours if checkout time is provided
        if self.checkin_time and self.checkout_time:
            self.calculate_work_hours()
            self.update_status()
    
    def calculate_work_hours(self):
        """Calculate work hours, break hours, and overtime"""
        if not self.checkin_time or not self.checkout_time:
            return
        
        # Calculate total hours worked
        checkin_datetime = f"{self.checkin_date} {self.checkin_time}"
        checkout_datetime = f"{self.checkin_date} {self.checkout_time}"
        
        total_hours = time_diff_in_hours(checkout_datetime, checkin_datetime)
        
        # Subtract break hours
        break_hours = flt(self.break_hours) or 0
        work_hours = total_hours - break_hours
        
        # Standard work hours (8 hours)
        standard_hours = 8.0
        
        if work_hours > standard_hours:
            self.work_hours = standard_hours
            self.overtime_hours = work_hours - standard_hours
        else:
            self.work_hours = work_hours
            self.overtime_hours = 0
    
    def update_status(self):
        """Update status based on check-in/out times"""
        if self.checkout_time:
            self.status = "Checked Out"
        else:
            self.status = "Checked In"
    
    def validate(self):
        """Additional validation"""
        # Validate coordinates
        if self.checkin_latitude and (self.checkin_latitude < -90 or self.checkin_latitude > 90):
            frappe.throw(_("Check-in Latitude must be between -90 and 90"))
            
        if self.checkin_longitude and (self.checkin_longitude < -180 or self.checkin_longitude > 180):
            frappe.throw(_("Check-in Longitude must be between -180 and 180"))
        
        # Validate checkout coordinates
        if self.checkout_latitude and (self.checkout_latitude < -90 or self.checkout_latitude > 90):
            frappe.throw(_("Check-out Latitude must be between -90 and 90"))
            
        if self.checkout_longitude and (self.checkout_longitude < -180 or self.checkout_longitude > 180):
            frappe.throw(_("Check-out Longitude must be between -180 and 180"))
        
        # Validate times
        if self.checkin_time and self.checkout_time:
            if get_time(self.checkout_time) <= get_time(self.checkin_time):
                frappe.throw(_("Check-out time must be after check-in time"))
    
    @frappe.whitelist()
    def checkout_worker(self, checkout_time=None, checkout_latitude=None, checkout_longitude=None, 
                       checkout_location=None, checkout_photo=None, notes=None):
        """Checkout worker with location and photo"""
        if self.checkout_time:
            frappe.throw(_("Worker is already checked out"))
        
        self.checkout_time = checkout_time or now().split()[1]
        
        if checkout_latitude:
            self.checkout_latitude = flt(checkout_latitude)
        if checkout_longitude:
            self.checkout_longitude = flt(checkout_longitude)
        if checkout_location:
            self.checkout_location = checkout_location
        if checkout_photo:
            self.checkout_photo = checkout_photo
        if notes:
            self.notes = notes
        
        self.calculate_work_hours()
        self.update_status()
        self.save()
        
        return {
            "status": "success",
            "message": _("Worker checked out successfully"),
            "work_hours": self.work_hours,
            "overtime_hours": self.overtime_hours
        }
    
    @frappe.whitelist()
    def get_location_distance(self):
        """Calculate distance between check-in and check-out locations"""
        if not all([self.checkin_latitude, self.checkin_longitude, 
                   self.checkout_latitude, self.checkout_longitude]):
            return None
        
        # Haversine formula for distance calculation
        import math
        
        lat1, lon1 = math.radians(self.checkin_latitude), math.radians(self.checkin_longitude)
        lat2, lon2 = math.radians(self.checkout_latitude), math.radians(self.checkout_longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return round(r * c, 2)


@frappe.whitelist()
def checkin_worker(worker, work_site, checkin_latitude=None, checkin_longitude=None, 
                  checkin_location=None, checkin_photo=None, notes=None):
    """API function to check in a worker"""
    
    # Check if worker is already checked in today
    existing = frappe.db.exists("Worker Checkin", {
        "worker": worker,
        "checkin_date": getdate(),
        "checkout_time": ["is", "not set"]
    })
    
    if existing:
        frappe.throw(_("Worker {0} is already checked in today").format(worker))
    
    # Create new checkin record
    checkin = frappe.get_doc({
        "doctype": "Worker Checkin",
        "worker": worker,
        "work_site": work_site,
        "checkin_date": getdate(),
        "checkin_time": now().split()[1],
        "checkin_latitude": flt(checkin_latitude) if checkin_latitude else None,
        "checkin_longitude": flt(checkin_longitude) if checkin_longitude else None,
        "checkin_location": checkin_location,
        "checkin_photo": checkin_photo,
        "notes": notes,
        "status": "Checked In"
    })
    
    checkin.insert()
    
    return {
        "status": "success",
        "message": _("Worker checked in successfully"),
        "checkin_id": checkin.name,
        "checkin_time": checkin.checkin_time
    }


@frappe.whitelist()
def get_worker_status(worker, date=None):
    """Get current status of a worker"""
    if not date:
        date = getdate()
    
    checkin = frappe.db.get_value("Worker Checkin", {
        "worker": worker,
        "checkin_date": date
    }, ["name", "work_site", "checkin_time", "checkout_time", "status"], as_dict=True)
    
    if not checkin:
        return {"status": "Not Checked In", "checkin": None}
    
    return {
        "status": checkin.status,
        "checkin": checkin
    }


@frappe.whitelist()
def get_site_attendance(work_site, date=None):
    """Get attendance summary for a work site"""
    if not date:
        date = getdate()
    
    attendance = frappe.db.sql("""
        SELECT 
            worker,
            worker_name,
            checkin_time,
            checkout_time,
            work_hours,
            overtime_hours,
            status
        FROM `tabWorker Checkin`
        WHERE work_site = %s AND checkin_date = %s
        ORDER BY checkin_time
    """, (work_site, date), as_dict=True)
    
    summary = {
        "total_workers": len(attendance),
        "checked_in": len([a for a in attendance if a.status == "Checked In"]),
        "checked_out": len([a for a in attendance if a.status == "Checked Out"]),
        "total_hours": sum([flt(a.work_hours) for a in attendance if a.work_hours]),
        "total_overtime": sum([flt(a.overtime_hours) for a in attendance if a.overtime_hours]),
        "attendance": attendance
    }
    
    return summary
