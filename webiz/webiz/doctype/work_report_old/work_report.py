# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, flt, add_days
from frappe import _


class WorkReport(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_by = frappe.session.user
        self.created_date = now()
        
    def before_save(self):
        """Validate and calculate values before saving"""
        self.modified_by = frappe.session.user
        self.modified_date = now()
        
        # Auto-populate attendance data
        self.populate_attendance_data()
        
        # Auto-populate checklist data
        self.populate_checklist_data()
        
        # Validate dates
        if self.work_start_date and self.work_end_date:
            if getdate(self.work_start_date) > getdate(self.work_end_date):
                frappe.throw(_("Work Start Date cannot be after Work End Date"))
    
    def populate_attendance_data(self):
        """Auto-populate worker attendance data"""
        if not self.work_site or not self.report_date:
            return
        
        # Get attendance data for the report date
        attendance_data = frappe.db.sql("""
            SELECT 
                COUNT(DISTINCT worker) as total_workers,
                SUM(work_hours) as total_work_hours,
                SUM(overtime_hours) as overtime_hours,
                SUM(break_hours) as break_hours
            FROM `tabWorker Checkin`
            WHERE work_site = %s 
            AND checkin_date = %s
            AND checkout_time IS NOT NULL
        """, (self.work_site, self.report_date), as_dict=True)
        
        if attendance_data and attendance_data[0]:
            data = attendance_data[0]
            self.total_workers = data.total_workers or 0
            self.total_work_hours = flt(data.total_work_hours) or 0
            self.total_attendance_hours = self.total_work_hours
            self.overtime_hours = flt(data.overtime_hours) or 0
            self.break_hours = flt(data.break_hours) or 0
        
        # Generate attendance summary text
        worker_details = frappe.db.sql("""
            SELECT worker_name, checkin_time, checkout_time, work_hours, overtime_hours
            FROM `tabWorker Checkin`
            WHERE work_site = %s 
            AND checkin_date = %s
            ORDER BY checkin_time
        """, (self.work_site, self.report_date), as_dict=True)
        
        if worker_details:
            summary_lines = []
            for worker in worker_details:
                line = f"{worker.worker_name}: {worker.checkin_time} - {worker.checkout_time or 'Not checked out'}"
                if worker.work_hours:
                    line += f" ({worker.work_hours}h"
                    if worker.overtime_hours:
                        line += f", OT: {worker.overtime_hours}h"
                    line += ")"
                summary_lines.append(line)
            
            self.worker_attendance_summary = "\n".join(summary_lines)
    
    def populate_checklist_data(self):
        """Auto-populate completed checklist data"""
        if not self.work_site or not self.report_date:
            return
        
        # Get completed checklists for the report date
        completed_checklists = frappe.get_all("Work Checklist",
            filters={
                "work_site": self.work_site,
                "completion_date": self.report_date,
                "status": "Completed"
            },
            fields=["name", "checklist_name", "completion_percentage", "achieved_score", "total_score"]
        )
        
        # Clear existing checklist references
        self.completed_checklists = []
        
        # Add completed checklists
        for checklist in completed_checklists:
            self.append("completed_checklists", {
                "work_checklist": checklist.name
            })
    
    def validate(self):
        """Additional validation"""
        # Check if work site exists
        if not frappe.db.exists("Work Site", self.work_site):
            frappe.throw(_("Work Site {0} does not exist").format(self.work_site))
        
        # Check if prepared by employee exists
        if not frappe.db.exists("Employee", self.prepared_by):
            frappe.throw(_("Employee {0} does not exist").format(self.prepared_by))
    
    def on_submit(self):
        """Actions to perform on submit"""
        self.status = "Submitted"

        # Send automatic report to stakeholders
        self.send_automatic_report()

        # Create follow-up tasks if needed
        if self.next_steps:
            self.create_follow_up_tasks()
    
    def on_cancel(self):
        """Actions to perform on cancel"""
        self.status = "Draft"
    
    def create_follow_up_tasks(self):
        """Create follow-up tasks based on next steps"""
        if not self.next_steps:
            return
        
        # Create a task for follow-up actions
        task = frappe.get_doc({
            "doctype": "Task",
            "subject": f"Follow-up: {self.report_title}",
            "description": self.next_steps,
            "project": self.project,
            "status": "Open",
            "priority": "Medium",
            "expected_start_date": add_days(getdate(), 1),
            "expected_end_date": add_days(getdate(), 7)
        })
        
        task.insert()
        
        frappe.msgprint(_("Follow-up task {0} created").format(task.name))

    def send_automatic_report(self):
        """Send automatic report to stakeholders"""
        try:
            # Get work site information
            work_site_doc = frappe.get_doc("Work Site", self.work_site)

            # Prepare recipient list
            recipients = []

            # Add customer contact
            if work_site_doc.customer:
                customer_contacts = frappe.get_all("Contact",
                    filters={"link_doctype": "Customer", "link_name": work_site_doc.customer},
                    fields=["email_id"]
                )
                for contact in customer_contacts:
                    if contact.email_id:
                        recipients.append(contact.email_id)

            # Add site manager
            if work_site_doc.site_manager:
                manager_email = frappe.db.get_value("Employee", work_site_doc.site_manager, "user_id")
                if manager_email:
                    recipients.append(manager_email)

            # Add supervisor
            if self.reviewed_by:
                supervisor_email = frappe.db.get_value("Employee", self.reviewed_by, "user_id")
                if supervisor_email:
                    recipients.append(supervisor_email)

            # Add prepared by
            if self.prepared_by:
                preparer_email = frappe.db.get_value("Employee", self.prepared_by, "user_id")
                if preparer_email:
                    recipients.append(preparer_email)

            # Remove duplicates
            recipients = list(set(recipients))

            if not recipients:
                frappe.log_error("No recipients found for work report", "Auto Report Send")
                return

            # Generate report content
            report_content = self.generate_email_content()

            # Send email
            frappe.sendmail(
                recipients=recipients,
                subject=f"현장 작업 보고서: {self.report_title}",
                message=report_content,
                attachments=[{
                    "fname": f"{self.name}.pdf",
                    "fcontent": self.get_pdf_content()
                }]
            )

            frappe.msgprint(_("Report sent automatically to {0} recipients").format(len(recipients)))

        except Exception as e:
            frappe.log_error(f"Auto report send failed: {str(e)}", "Auto Report Send")
            frappe.msgprint(_("Failed to send automatic report. Please send manually."))

    def generate_email_content(self):
        """Generate email content for the report"""
        work_site_doc = frappe.get_doc("Work Site", self.work_site)

        content = f"""
        <h2>현장 작업 보고서</h2>

        <h3>기본 정보</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr><td><strong>보고서 제목</strong></td><td>{self.report_title}</td></tr>
            <tr><td><strong>현장명</strong></td><td>{work_site_doc.site_name}</td></tr>
            <tr><td><strong>고객</strong></td><td>{work_site_doc.customer}</td></tr>
            <tr><td><strong>작업 날짜</strong></td><td>{self.report_date}</td></tr>
            <tr><td><strong>작성자</strong></td><td>{frappe.db.get_value("Employee", self.prepared_by, "employee_name") if self.prepared_by else ""}</td></tr>
        </table>

        <h3>작업 요약</h3>
        <div>{self.work_summary or "작업 요약이 없습니다."}</div>

        <h3>작업자 현황</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr><td><strong>총 작업자 수</strong></td><td>{self.total_workers or 0}명</td></tr>
            <tr><td><strong>총 작업 시간</strong></td><td>{self.total_work_hours or 0}시간</td></tr>
            <tr><td><strong>연장 근무</strong></td><td>{self.overtime_hours or 0}시간</td></tr>
        </table>

        <h3>작업자 출근 현황</h3>
        <pre>{self.worker_attendance_summary or "출근 현황 정보가 없습니다."}</pre>
        """

        # Add completed checklists
        if self.completed_checklists:
            content += "<h3>완료된 체크리스트</h3><ul>"
            for checklist_ref in self.completed_checklists:
                checklist_doc = frappe.get_doc("Work Checklist", checklist_ref.work_checklist)
                content += f"<li>{checklist_doc.checklist_name} (완료율: {checklist_doc.completion_percentage}%)</li>"
            content += "</ul>"

        # Add issues if any
        if self.issues_encountered:
            content += f"<h3>발생한 문제점</h3><div>{self.issues_encountered}</div>"

        if self.safety_incidents:
            content += f"<h3>안전 사고</h3><div>{self.safety_incidents}</div>"

        # Add recommendations
        if self.recommendations:
            content += f"<h3>권고사항</h3><div>{self.recommendations}</div>"

        if self.next_steps:
            content += f"<h3>다음 단계</h3><div>{self.next_steps}</div>"

        content += """
        <hr>
        <p><small>이 보고서는 자동으로 생성되어 발송되었습니다.
        자세한 내용은 첨부된 PDF 파일을 확인해주세요.</small></p>
        """

        return content

    def get_pdf_content(self):
        """Generate PDF content for the report"""
        try:
            # Use Frappe's PDF generation
            html = frappe.get_print(self.doctype, self.name, print_format="Standard")
            pdf = frappe.utils.pdf.get_pdf(html)
            return pdf
        except Exception as e:
            frappe.log_error(f"PDF generation failed: {str(e)}")
            return None
    
    @frappe.whitelist()
    def generate_auto_report(self):
        """Auto-generate report content based on data"""
        if not self.work_site or not self.report_date:
            frappe.throw(_("Work Site and Report Date are required"))
        
        # Generate work summary
        summary_parts = []
        
        if self.total_workers:
            summary_parts.append(f"총 {self.total_workers}명의 작업자가 참여")
        
        if self.total_work_hours:
            summary_parts.append(f"총 {self.total_work_hours}시간의 작업 수행")
        
        if self.overtime_hours:
            summary_parts.append(f"연장근무 {self.overtime_hours}시간")
        
        # Get checklist completion info
        completed_count = len(self.completed_checklists) if self.completed_checklists else 0
        if completed_count:
            summary_parts.append(f"{completed_count}개의 체크리스트 완료")
        
        if summary_parts:
            self.work_summary = f"<p>{self.report_date} 작업 요약:</p><ul>" + \
                              "".join([f"<li>{part}</li>" for part in summary_parts]) + "</ul>"
        
        # Generate detailed description
        description_parts = []
        
        if self.worker_attendance_summary:
            description_parts.append(f"작업자 출근 현황:\n{self.worker_attendance_summary}")
        
        if self.completed_checklists:
            checklist_names = []
            for cl in self.completed_checklists:
                checklist_doc = frappe.get_doc("Work Checklist", cl.work_checklist)
                checklist_names.append(f"- {checklist_doc.checklist_name} (완료율: {checklist_doc.completion_percentage}%)")
            
            if checklist_names:
                description_parts.append(f"완료된 체크리스트:\n" + "\n".join(checklist_names))
        
        if description_parts:
            self.work_description = "\n\n".join(description_parts)
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Report content generated successfully")
        }
    
    @frappe.whitelist()
    def submit_for_review(self, reviewer=None):
        """Submit report for review"""
        if self.status != "Draft":
            frappe.throw(_("Only draft reports can be submitted for review"))
        
        self.status = "Under Review"
        if reviewer:
            self.reviewed_by = reviewer
        
        self.save()
        
        # Send notification to reviewer
        if self.reviewed_by:
            frappe.sendmail(
                recipients=[frappe.db.get_value("Employee", self.reviewed_by, "user_id")],
                subject=f"Work Report Review Required: {self.report_title}",
                message=f"Please review the work report: {self.name}"
            )
        
        return {
            "status": "success",
            "message": _("Report submitted for review")
        }
    
    @frappe.whitelist()
    def approve_report(self, comments=None):
        """Approve the report"""
        if self.status != "Under Review":
            frappe.throw(_("Only reports under review can be approved"))
        
        self.status = "Approved"
        self.approved_by = frappe.session.user
        
        if comments:
            self.supervisor_comments = comments
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Report approved successfully")
        }
    
    @frappe.whitelist()
    def reject_report(self, reason=None):
        """Reject the report"""
        if self.status != "Under Review":
            frappe.throw(_("Only reports under review can be rejected"))
        
        self.status = "Rejected"
        
        if reason:
            self.supervisor_comments = reason
        
        self.save()
        
        return {
            "status": "success",
            "message": _("Report rejected")
        }
    
    def get_dashboard_data(self):
        """Return data for dashboard"""
        return {
            "fieldname": "work_report",
            "transactions": [
                {
                    "label": _("Work Management"),
                    "items": ["Work Checklist", "Worker Checkin"]
                },
                {
                    "label": _("Project Management"),
                    "items": ["Task", "Project"]
                }
            ]
        }


@frappe.whitelist()
def create_daily_report(work_site, report_date=None, prepared_by=None):
    """Create a daily work report"""
    if not report_date:
        report_date = getdate()
    
    if not prepared_by:
        prepared_by = frappe.session.user
    
    # Check if report already exists
    existing = frappe.db.exists("Work Report", {
        "work_site": work_site,
        "report_date": report_date,
        "report_type": "Daily"
    })
    
    if existing:
        frappe.throw(_("Daily report for {0} on {1} already exists").format(work_site, report_date))
    
    # Get work site info
    work_site_doc = frappe.get_doc("Work Site", work_site)
    
    # Create report
    report = frappe.get_doc({
        "doctype": "Work Report",
        "report_title": f"Daily Report - {work_site_doc.site_name} - {report_date}",
        "work_site": work_site,
        "project": work_site_doc.project,
        "report_date": report_date,
        "report_type": "Daily",
        "prepared_by": prepared_by,
        "work_start_date": report_date,
        "work_end_date": report_date,
        "status": "Draft"
    })
    
    report.insert()
    
    # Auto-generate content
    report.generate_auto_report()
    
    return report.name
