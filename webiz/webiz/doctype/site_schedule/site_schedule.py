# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, get_time, add_days, time_diff_in_hours
from frappe import _


class SiteSchedule(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and set values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Validate times
        if self.start_time and self.end_time:
            if get_time(self.start_time) >= get_time(self.end_time):
                frappe.throw(_("End Time must be after Start Time"))
        
        # Calculate estimated duration if not set
        if self.start_time and self.end_time and not self.estimated_duration:
            start_datetime = f"{self.scheduled_date} {self.start_time}"
            end_datetime = f"{self.scheduled_date} {self.end_time}"
            self.estimated_duration = time_diff_in_hours(end_datetime, start_datetime)
    
    def validate(self):
        """Additional validation"""
        # Check if employee exists
        if not frappe.db.exists("Employee", self.employee):
            frappe.throw(_("Employee {0} does not exist").format(self.employee))
        
        # Check if work site exists
        if not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("Work Site {0} does not exist").format(self.work_site))
        
        # Check for scheduling conflicts
        self.check_scheduling_conflicts()
    
    def check_scheduling_conflicts(self):
        """Check for scheduling conflicts with other schedules"""
        if self.status == "Cancelled":
            return
        
        conflicts = frappe.db.sql("""
            SELECT name, schedule_title, start_time, end_time
            FROM `tabSite Schedule`
            WHERE employee = %s 
            AND scheduled_date = %s
            AND status NOT IN ('Cancelled', 'Completed')
            AND name != %s
            AND (
                (start_time <= %s AND end_time > %s) OR
                (start_time < %s AND end_time >= %s) OR
                (start_time >= %s AND end_time <= %s)
            )
        """, (
            self.employee, self.scheduled_date, self.name or '',
            self.start_time, self.start_time,
            self.end_time, self.end_time,
            self.start_time, self.end_time
        ), as_dict=True)
        
        if conflicts:
            conflict_details = ", ".join([f"{c.schedule_title} ({c.start_time}-{c.end_time})" for c in conflicts])
            frappe.throw(_("Scheduling conflict detected with: {0}").format(conflict_details))
    
    def on_update(self):
        """Actions to perform after update"""
        # Send notification if status changed to Confirmed
        if self.has_value_changed("status") and self.status == "Confirmed":
            self.send_confirmation_notification()
        
        # Auto-create checklist if enabled
        if self.auto_create_checklist and self.checklist_template and self.status == "Confirmed":
            self.create_work_checklist()
    
    def send_confirmation_notification(self):
        """Send confirmation notification to employee"""
        if not self.notification_sent:
            employee_email = frappe.db.get_value("Employee", self.employee, "user_id")
            if employee_email:
                frappe.sendmail(
                    recipients=[employee_email],
                    subject=f"현장 방문 일정 확정: {self.schedule_title}",
                    message=f"""
                    안녕하세요 {self.employee_name}님,
                    
                    다음 현장 방문 일정이 확정되었습니다:
                    
                    - 일정명: {self.schedule_title}
                    - 현장: {self.site_name}
                    - 날짜: {self.scheduled_date}
                    - 시간: {self.start_time} - {self.end_time}
                    - 고객: {self.customer}
                    
                    업무 내용:
                    {self.work_description or '상세 내용은 시스템에서 확인해주세요.'}
                    
                    특별 지시사항:
                    {self.special_instructions or '없음'}
                    
                    현장 접근 방법:
                    {self.access_instructions or '별도 안내 없음'}
                    
                    안전한 업무 수행 부탁드립니다.
                    """
                )
                self.notification_sent = 1
                self.save()
    
    def create_work_checklist(self):
        """Auto-create work checklist based on template"""
        if not self.checklist_template:
            return
        
        # Check if checklist already exists
        existing = frappe.db.exists("Work Checklist", {
            "work_site": self.work_site,
            "assigned_to": self.employee,
            "due_date": self.scheduled_date,
            "checklist_type": self.checklist_template
        })
        
        if existing:
            return
        
        # Create checklist using API
        from webiz.api.work_management import create_checklist_from_template
        
        checklist_name = create_checklist_from_template(
            template_name=self.checklist_template,
            work_site=self.work_site,
            assigned_to=self.employee,
            due_date=self.scheduled_date
        )
        
        frappe.msgprint(_("Work checklist {0} created automatically").format(checklist_name))
    
    @frappe.whitelist()
    def start_work(self):
        """Mark work as started"""
        if self.status != "Confirmed":
            frappe.throw(_("Only confirmed schedules can be started"))
        
        self.status = "In Progress"
        self.actual_start_time = now()
        self.save()
        
        return {
            "status": "success",
            "message": _("Work started successfully"),
            "start_time": self.actual_start_time
        }
    
    @frappe.whitelist()
    def complete_work(self, completion_status=None, worker_notes=None):
        """Mark work as completed"""
        if self.status != "In Progress":
            frappe.throw(_("Only work in progress can be completed"))
        
        self.status = "Completed"
        self.actual_end_time = now()
        self.completion_status = completion_status or "Completed"
        
        if worker_notes:
            self.worker_notes = worker_notes
        
        self.save()
        
        # Auto-create work report
        self.create_work_report()
        
        return {
            "status": "success",
            "message": _("Work completed successfully"),
            "end_time": self.actual_end_time
        }
    
    def create_work_report(self):
        """Auto-create work report after completion"""
        from webiz.webiz.doctype.work_report.work_report import create_daily_report
        
        try:
            report_name = create_daily_report(
                work_site=self.work_site,
                report_date=self.scheduled_date,
                prepared_by=self.employee
            )
            frappe.msgprint(_("Work report {0} created automatically").format(report_name))
        except Exception as e:
            frappe.log_error(f"Auto report creation failed: {str(e)}")
    
    @frappe.whitelist()
    def send_reminder(self):
        """Send reminder notification"""
        employee_email = frappe.db.get_value("Employee", self.employee, "user_id")
        if employee_email:
            frappe.sendmail(
                recipients=[employee_email],
                subject=f"현장 방문 일정 알림: {self.schedule_title}",
                message=f"""
                안녕하세요 {self.employee_name}님,
                
                내일 현장 방문 일정을 알려드립니다:
                
                - 일정명: {self.schedule_title}
                - 현장: {self.site_name}
                - 날짜: {self.scheduled_date}
                - 시간: {self.start_time} - {self.end_time}
                
                필요 장비: {self.required_equipment or '없음'}
                안전 요구사항: {self.safety_requirements or '기본 안전수칙 준수'}
                
                준비사항을 미리 확인해주세요.
                """
            )
            self.reminder_sent = 1
            self.save()
            
            return {"status": "success", "message": _("Reminder sent successfully")}
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "site_schedule",
            "transactions": [
                {
                    "label": _("Site Management"),
                    "items": ["Worker Checkin", "Work Checklist", "Work Report"]
                },
                {
                    "label": _("Project Management"),
                    "items": ["Task", "Timesheet"]
                }
            ]
        }


@frappe.whitelist()
def get_employee_schedule(employee, date_from=None, date_to=None):
    """Get schedule for an employee"""
    if not date_from:
        date_from = getdate()
    if not date_to:
        date_to = add_days(getdate(), 7)
    
    schedules = frappe.get_all("Site Schedule",
        filters={
            "employee": employee,
            "scheduled_date": ["between", [date_from, date_to]],
            "status": ["!=", "Cancelled"]
        },
        fields=[
            "name", "schedule_title", "work_site", "site_name", "customer",
            "scheduled_date", "start_time", "end_time", "status", "priority",
            "work_description", "special_instructions", "estimated_duration"
        ],
        order_by="scheduled_date asc, start_time asc"
    )
    
    return schedules


@frappe.whitelist()
def get_today_schedule(employee=None):
    """Get today's schedule for an employee"""
    if not employee:
        employee = frappe.session.user
    
    # Get employee record from user
    employee_doc = frappe.db.get_value("Employee", {"user_id": employee}, "name")
    if not employee_doc:
        return []
    
    return get_employee_schedule(employee_doc, getdate(), getdate())


@frappe.whitelist()
def create_recurring_schedule(schedule_data, recurrence_pattern, end_date):
    """Create recurring schedules"""
    import json
    from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
    from datetime import datetime
    
    if isinstance(schedule_data, str):
        schedule_data = json.loads(schedule_data)
    
    base_date = datetime.strptime(schedule_data["scheduled_date"], "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Define recurrence rules
    freq_map = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY}
    freq = freq_map.get(recurrence_pattern.lower(), WEEKLY)
    
    dates = list(rrule(freq, dtstart=base_date, until=end_date))
    
    created_schedules = []
    
    for date in dates:
        schedule_data["scheduled_date"] = date.strftime("%Y-%m-%d")
        schedule_data["schedule_title"] = f"{schedule_data['schedule_title']} - {date.strftime('%Y-%m-%d')}"
        
        schedule = frappe.get_doc({
            "doctype": "Site Schedule",
            **schedule_data
        })
        schedule.insert()
        created_schedules.append(schedule.name)
    
    return {
        "status": "success",
        "message": _("{0} schedules created").format(len(created_schedules)),
        "schedules": created_schedules
    }
