# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, now, flt
import json


@frappe.whitelist()
def get_work_site_dashboard(work_site):
    """Get comprehensive dashboard data for a work site"""
    if not frappe.db.exists("Work Site", work_site):
        frappe.throw(_("Work Site {0} does not exist").format(work_site))
    
    site_doc = frappe.get_doc("Work Site", work_site)
    
    # Get today's attendance
    today_attendance = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_checkins,
            COUNT(CASE WHEN checkout_time IS NULL THEN 1 END) as currently_present,
            SUM(work_hours) as total_work_hours,
            SUM(overtime_hours) as total_overtime
        FROM `tabWorker Checkin`
        WHERE work_site = %s AND checkin_date = %s
    """, (work_site, getdate()), as_dict=True)[0]
    
    # Get pending checklists
    pending_checklists = frappe.db.count("Work Checklist", {
        "work_site": work_site,
        "status": ["in", ["Pending", "In Progress"]]
    })
    
    # Get completed checklists today
    completed_today = frappe.db.count("Work Checklist", {
        "work_site": work_site,
        "status": "Completed",
        "completion_date": getdate()
    })
    
    # Get recent reports
    recent_reports = frappe.get_all("Work Report",
        filters={"work_site": work_site},
        fields=["name", "report_title", "report_date", "status"],
        order_by="report_date desc",
        limit=5
    )
    
    return {
        "site_info": {
            "name": site_doc.name,
            "site_name": site_doc.site_name,
            "customer": site_doc.customer,
            "status": site_doc.status,
            "site_manager": site_doc.site_manager,
            "location": site_doc.get_location_info()
        },
        "attendance": {
            "total_checkins": today_attendance.total_checkins or 0,
            "currently_present": today_attendance.currently_present or 0,
            "total_work_hours": flt(today_attendance.total_work_hours) or 0,
            "total_overtime": flt(today_attendance.total_overtime) or 0
        },
        "checklists": {
            "pending": pending_checklists,
            "completed_today": completed_today
        },
        "recent_reports": recent_reports
    }


@frappe.whitelist()
def qr_checkin(worker, qr_data, photo=None, notes=None):
    """QR code-based worker check-in"""
    try:
        import json

        # Parse QR data
        qr_info = json.loads(qr_data)

        # Validate QR code (support both old and new format)
        qr_type = qr_info.get("type") or qr_info.get("t")
        if qr_type not in ["work_site_checkin", "wsc"]:
            return {"status": "error", "message": _("Invalid QR code type")}

        work_site = qr_info.get("work_site") or qr_info.get("ws")
        if not work_site:
            return {"status": "error", "message": _("Work site not found in QR code")}

        # Validate work site exists and QR is enabled
        site_doc = frappe.get_doc("Work Site", work_site)
        if not site_doc.qr_enabled:
            return {"status": "error", "message": _("QR check-in is disabled for this site")}

        # Use regular mobile checkin with QR data
        result = mobile_checkin(
            worker=worker,
            work_site=work_site,
            photo=photo,
            notes=f"QR Check-in: {notes}" if notes else "QR Check-in"
        )

        if result.get("status") == "success":
            result["message"] = _("QR Check-in successful at {0}").format(site_doc.site_name)

        return result

    except json.JSONDecodeError:
        return {"status": "error", "message": _("Invalid QR code format")}
    except Exception as e:
        frappe.log_error(f"QR checkin error: {str(e)}")
        return {"status": "error", "message": _("QR Check-in failed. Please try again.")}


@frappe.whitelist()
def mobile_checkin(worker, work_site, latitude=None, longitude=None, photo=None, notes=None):
    """Mobile-friendly worker check-in API"""
    try:
        # Validate inputs
        if not frappe.db.exists("Employee", worker):
            return {"status": "error", "message": _("Invalid worker ID")}
        
        if not frappe.db.exists("Work Site", work_site):
            return {"status": "error", "message": _("Invalid work site")}
        
        # Check if already checked in today
        existing = frappe.db.exists("Worker Checkin", {
            "worker": worker,
            "checkin_date": getdate(),
            "checkout_time": ["is", "not set"]
        })
        
        if existing:
            return {"status": "error", "message": _("Already checked in today")}
        
        # Create checkin record
        checkin = frappe.get_doc({
            "doctype": "Worker Checkin",
            "worker": worker,
            "work_site": work_site,
            "checkin_date": getdate(),
            "checkin_time": now().split()[1],
            "checkin_latitude": flt(latitude) if latitude else None,
            "checkin_longitude": flt(longitude) if longitude else None,
            "checkin_photo": photo,
            "notes": notes,
            "status": "Checked In"
        })
        
        checkin.insert()
        
        return {
            "status": "success",
            "message": _("Check-in successful"),
            "checkin_id": checkin.name,
            "checkin_time": checkin.checkin_time
        }
        
    except Exception as e:
        frappe.log_error(f"Mobile checkin error: {str(e)}")
        return {"status": "error", "message": _("Check-in failed. Please try again.")}


@frappe.whitelist()
def mobile_checkout(worker, latitude=None, longitude=None, photo=None, notes=None):
    """Mobile-friendly worker check-out API"""
    try:
        # Find today's checkin record
        checkin_name = frappe.db.get_value("Worker Checkin", {
            "worker": worker,
            "checkin_date": getdate(),
            "checkout_time": ["is", "not set"]
        })
        
        if not checkin_name:
            return {"status": "error", "message": _("No active check-in found for today")}
        
        checkin = frappe.get_doc("Worker Checkin", checkin_name)
        
        result = checkin.checkout_worker(
            checkout_time=now().split()[1],
            checkout_latitude=latitude,
            checkout_longitude=longitude,
            checkout_photo=photo,
            notes=notes
        )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Mobile checkout error: {str(e)}")
        return {"status": "error", "message": _("Check-out failed. Please try again.")}


@frappe.whitelist()
def get_worker_checklists(worker, work_site=None, status=None):
    """Get checklists assigned to a worker"""
    filters = {"assigned_to": worker}
    
    if work_site:
        filters["work_site"] = work_site
    
    if status:
        filters["status"] = status
    else:
        filters["status"] = ["in", ["Pending", "In Progress"]]
    
    checklists = frappe.get_all("Work Checklist",
        filters=filters,
        fields=[
            "name", "checklist_name", "work_site", "status", "priority",
            "due_date", "completion_percentage", "checklist_type"
        ],
        order_by="due_date asc, priority desc"
    )
    
    return checklists


@frappe.whitelist()
def update_checklist_item(checklist_name, item_idx, is_completed, score=None, notes=None, photo=None):
    """Update a specific checklist item"""
    try:
        checklist = frappe.get_doc("Work Checklist", checklist_name)
        
        # Check permissions
        if checklist.assigned_to != frappe.session.user and not frappe.has_permission("Work Checklist", "write"):
            return {"status": "error", "message": _("Not authorized to update this checklist")}
        
        item_idx = int(item_idx)
        if item_idx >= len(checklist.checklist_items):
            return {"status": "error", "message": _("Invalid item index")}
        
        if is_completed:
            result = checklist.mark_item_completed(item_idx, score=score, notes=notes, photo=photo)
        else:
            result = checklist.mark_item_incomplete(item_idx)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Update checklist item error: {str(e)}")
        return {"status": "error", "message": _("Failed to update checklist item")}


@frappe.whitelist()
def create_quick_checklist(work_site, checklist_name, assigned_to, items_json):
    """Create a quick checklist with items"""
    try:
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        
        checklist = frappe.get_doc({
            "doctype": "Work Checklist",
            "checklist_name": checklist_name,
            "work_site": work_site,
            "assigned_to": assigned_to,
            "due_date": getdate(),
            "status": "Pending",
            "checklist_type": "Daily"
        })
        
        for item in items:
            checklist.append("checklist_items", {
                "item_name": item.get("name"),
                "description": item.get("description", ""),
                "item_type": item.get("type", "Task"),
                "is_mandatory": item.get("mandatory", 0),
                "max_score": item.get("max_score", 10)
            })
        
        checklist.insert()
        
        return {
            "status": "success",
            "message": _("Checklist created successfully"),
            "checklist_id": checklist.name
        }
        
    except Exception as e:
        frappe.log_error(f"Create quick checklist error: {str(e)}")
        return {"status": "error", "message": _("Failed to create checklist")}


@frappe.whitelist()
def get_site_statistics(work_site, date_from=None, date_to=None):
    """Get comprehensive statistics for a work site"""
    if not date_from:
        date_from = getdate()
    if not date_to:
        date_to = getdate()
    
    # Worker attendance statistics
    attendance_stats = frappe.db.sql("""
        SELECT 
            COUNT(DISTINCT worker) as unique_workers,
            COUNT(*) as total_checkins,
            AVG(work_hours) as avg_work_hours,
            SUM(work_hours) as total_work_hours,
            SUM(overtime_hours) as total_overtime_hours
        FROM `tabWorker Checkin`
        WHERE work_site = %s 
        AND checkin_date BETWEEN %s AND %s
        AND checkout_time IS NOT NULL
    """, (work_site, date_from, date_to), as_dict=True)[0]
    
    # Checklist statistics
    checklist_stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_checklists,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_checklists,
            AVG(completion_percentage) as avg_completion_rate,
            AVG(achieved_score/total_score * 100) as avg_quality_score
        FROM `tabWork Checklist`
        WHERE work_site = %s 
        AND creation BETWEEN %s AND %s
    """, (work_site, date_from, date_to), as_dict=True)[0]
    
    # Report statistics
    report_stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_reports,
            COUNT(CASE WHEN status = 'Approved' THEN 1 END) as approved_reports
        FROM `tabWork Report`
        WHERE work_site = %s 
        AND report_date BETWEEN %s AND %s
    """, (work_site, date_from, date_to), as_dict=True)[0]
    
    return {
        "period": {"from": date_from, "to": date_to},
        "attendance": {
            "unique_workers": attendance_stats.unique_workers or 0,
            "total_checkins": attendance_stats.total_checkins or 0,
            "avg_work_hours": flt(attendance_stats.avg_work_hours, 2) or 0,
            "total_work_hours": flt(attendance_stats.total_work_hours, 2) or 0,
            "total_overtime_hours": flt(attendance_stats.total_overtime_hours, 2) or 0
        },
        "checklists": {
            "total_checklists": checklist_stats.total_checklists or 0,
            "completed_checklists": checklist_stats.completed_checklists or 0,
            "completion_rate": flt(checklist_stats.avg_completion_rate, 2) or 0,
            "quality_score": flt(checklist_stats.avg_quality_score, 2) or 0
        },
        "reports": {
            "total_reports": report_stats.total_reports or 0,
            "approved_reports": report_stats.approved_reports or 0
        }
    }


@frappe.whitelist()
def complete_site_work(work_site, employee, completion_notes=None, auto_send_report=True):
    """Complete all work for a site and generate report"""
    try:
        # Check if employee has active checkin
        checkin = frappe.db.get_value("Worker Checkin", {
            "worker": employee,
            "work_site": work_site,
            "checkin_date": getdate(),
            "checkout_time": ["is", "not set"]
        })

        if not checkin:
            return {"status": "error", "message": _("No active check-in found for today")}

        # Checkout worker
        checkin_doc = frappe.get_doc("Worker Checkin", checkin)
        checkout_result = checkin_doc.checkout_worker(
            checkout_time=now().split()[1],
            notes=completion_notes
        )

        if checkout_result.get("status") != "success":
            return checkout_result

        # Complete any pending checklists
        pending_checklists = frappe.get_all("Work Checklist", {
            "work_site": work_site,
            "assigned_to": employee,
            "status": ["in", ["Pending", "In Progress"]],
            "due_date": getdate()
        })

        completed_checklists = []
        for checklist in pending_checklists:
            try:
                checklist_doc = frappe.get_doc("Work Checklist", checklist.name)
                # Auto-complete if all mandatory items are done
                mandatory_items = [item for item in checklist_doc.checklist_items if item.is_mandatory]
                completed_mandatory = [item for item in mandatory_items if item.is_completed]

                if len(mandatory_items) == len(completed_mandatory):
                    checklist_doc.complete_checklist(
                        supervisor_comments="Auto-completed on work completion"
                    )
                    completed_checklists.append(checklist.name)
            except Exception as e:
                frappe.log_error(f"Failed to complete checklist {checklist.name}: {str(e)}")

        # Generate work report
        from webiz.webiz.doctype.work_report.work_report import create_daily_report

        report_name = create_daily_report(
            work_site=work_site,
            report_date=getdate(),
            prepared_by=employee
        )

        report_doc = frappe.get_doc("Work Report", report_name)

        # Add completion notes
        if completion_notes:
            report_doc.worker_comments = completion_notes

        # Auto-generate content
        report_doc.generate_auto_report()

        # Submit and send if requested
        if auto_send_report:
            report_doc.submit()

        return {
            "status": "success",
            "message": _("Work completed successfully"),
            "checkout_time": checkout_result.get("work_hours"),
            "work_hours": checkout_result.get("work_hours"),
            "completed_checklists": completed_checklists,
            "report_name": report_name,
            "report_sent": auto_send_report
        }

    except Exception as e:
        frappe.log_error(f"Complete site work error: {str(e)}")
        return {"status": "error", "message": _("Failed to complete work. Please try again.")}


@frappe.whitelist()
def send_daily_reports_batch(date=None):
    """Send daily reports for all active sites (scheduled function)"""
    if not date:
        date = getdate()

    # Get all active work sites with completed work today
    sites_with_work = frappe.db.sql("""
        SELECT DISTINCT wc.work_site, ws.site_name, ws.customer
        FROM `tabWorker Checkin` wc
        JOIN `tabWork Site` ws ON wc.work_site = ws.name
        WHERE wc.checkin_date = %s
        AND wc.checkout_time IS NOT NULL
        AND ws.status = 'Active'
    """, (date,), as_dict=True)

    sent_reports = []
    failed_reports = []

    for site in sites_with_work:
        try:
            # Check if report already exists
            existing_report = frappe.db.exists("Work Report", {
                "work_site": site.work_site,
                "report_date": date,
                "report_type": "Daily"
            })

            if existing_report:
                report_doc = frappe.get_doc("Work Report", existing_report)
                if report_doc.docstatus == 0:  # Draft
                    report_doc.generate_auto_report()
                    report_doc.submit()
                    sent_reports.append(site.work_site)
            else:
                # Create new report
                from webiz.webiz.doctype.work_report.work_report import create_daily_report

                # Get primary worker for the site today
                primary_worker = frappe.db.get_value("Worker Checkin", {
                    "work_site": site.work_site,
                    "checkin_date": date
                }, "worker")

                if primary_worker:
                    report_name = create_daily_report(
                        work_site=site.work_site,
                        report_date=date,
                        prepared_by=primary_worker
                    )

                    report_doc = frappe.get_doc("Work Report", report_name)
                    report_doc.generate_auto_report()
                    report_doc.submit()
                    sent_reports.append(site.work_site)

        except Exception as e:
            frappe.log_error(f"Failed to send report for {site.work_site}: {str(e)}")
            failed_reports.append(site.work_site)

    return {
        "status": "success",
        "sent_reports": len(sent_reports),
        "failed_reports": len(failed_reports),
        "details": {
            "sent": sent_reports,
            "failed": failed_reports
        }
    }


@frappe.whitelist()
def get_work_completion_summary(work_site, date=None):
    """Get work completion summary for a site"""
    if not date:
        date = getdate()

    # Get attendance summary
    attendance = frappe.db.sql("""
        SELECT
            COUNT(*) as total_workers,
            SUM(work_hours) as total_hours,
            SUM(overtime_hours) as overtime_hours,
            MIN(checkin_time) as first_checkin,
            MAX(checkout_time) as last_checkout
        FROM `tabWorker Checkin`
        WHERE work_site = %s AND checkin_date = %s
        AND checkout_time IS NOT NULL
    """, (work_site, date), as_dict=True)[0]

    # Get checklist summary
    checklists = frappe.db.sql("""
        SELECT
            COUNT(*) as total_checklists,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_checklists,
            AVG(completion_percentage) as avg_completion
        FROM `tabWork Checklist`
        WHERE work_site = %s AND due_date = %s
    """, (work_site, date), as_dict=True)[0]

    # Get any issues or incidents
    issues = frappe.get_all("Work Report",
        filters={
            "work_site": work_site,
            "report_date": date
        },
        fields=["issues_encountered", "safety_incidents", "quality_issues"]
    )

    return {
        "date": date,
        "work_site": work_site,
        "attendance": attendance,
        "checklists": checklists,
        "issues": issues[0] if issues else None,
        "completion_rate": (checklists.completed_checklists / checklists.total_checklists * 100) if checklists.total_checklists else 0
    }


@frappe.whitelist()
def get_worker_performance(worker, date_from=None, date_to=None):
    """Get performance metrics for a worker"""
    if not date_from:
        date_from = getdate()
    if not date_to:
        date_to = getdate()
    
    # Attendance performance
    attendance = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_days,
            AVG(work_hours) as avg_work_hours,
            SUM(overtime_hours) as total_overtime,
            COUNT(CASE WHEN status = 'Late' THEN 1 END) as late_days
        FROM `tabWorker Checkin`
        WHERE worker = %s 
        AND checkin_date BETWEEN %s AND %s
        AND checkout_time IS NOT NULL
    """, (worker, date_from, date_to), as_dict=True)[0]
    
    # Checklist performance
    checklists = frappe.db.sql("""
        SELECT 
            COUNT(*) as assigned_checklists,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_checklists,
            AVG(completion_percentage) as avg_completion_rate,
            AVG(achieved_score/total_score * 100) as avg_quality_score
        FROM `tabWork Checklist`
        WHERE assigned_to = %s 
        AND creation BETWEEN %s AND %s
    """, (worker, date_from, date_to), as_dict=True)[0]
    
    return {
        "worker": worker,
        "period": {"from": date_from, "to": date_to},
        "attendance": {
            "total_days": attendance.total_days or 0,
            "avg_work_hours": flt(attendance.avg_work_hours, 2) or 0,
            "total_overtime": flt(attendance.total_overtime, 2) or 0,
            "late_days": attendance.late_days or 0,
            "punctuality_rate": ((attendance.total_days - attendance.late_days) / attendance.total_days * 100) if attendance.total_days else 0
        },
        "checklists": {
            "assigned": checklists.assigned_checklists or 0,
            "completed": checklists.completed_checklists or 0,
            "completion_rate": flt(checklists.avg_completion_rate, 2) or 0,
            "quality_score": flt(checklists.avg_quality_score, 2) or 0
        }
    }
