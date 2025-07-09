# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, now, flt
import json


@frappe.whitelist()
def simple_qr_checkin(worker, qr_data):
    """단순화된 QR 체크인 - 체크인 후 바로 체크리스트 반환"""
    try:
        # QR 데이터 파싱
        qr_info = json.loads(qr_data)
        work_location = qr_info.get("work_location")
        
        if not work_location:
            return {"status": "error", "message": _("잘못된 QR 코드입니다")}
        
        # 작업장소 정보 확인
        location_doc = frappe.get_doc("Work Site", work_location)
        if not location_doc.qr_enabled:
            return {"status": "error", "message": _("이 장소는 QR 체크인이 비활성화되어 있습니다")}
        
        # 오늘 이미 체크인했는지 확인
        existing_checkin = frappe.db.exists("Worker Checkin", {
            "worker": worker,
            "work_site": work_location,
            "checkin_date": getdate(),
            "checkout_time": ["is", "not set"]
        })
        
        if existing_checkin:
            # 이미 체크인된 경우 체크리스트만 반환
            checklists = get_location_checklists(work_location, worker)
            return {
                "status": "already_checked_in",
                "message": _("이미 체크인되어 있습니다"),
                "checklists": checklists,
                "checkin_id": existing_checkin
            }
        
        # 새로운 체크인 생성
        checkin = frappe.get_doc({
            "doctype": "Worker Checkin",
            "worker": worker,
            "work_site": work_location,
            "checkin_date": getdate(),
            "checkin_time": now().split()[1],
            "status": "Checked In"
        })
        checkin.insert()
        
        # 해당 장소의 체크리스트 가져오기
        checklists = get_location_checklists(work_location, worker)
        
        return {
            "status": "success",
            "message": _("체크인 완료"),
            "checkin_id": checkin.name,
            "location_name": location_doc.site_name,
            "checklists": checklists
        }
        
    except Exception as e:
        frappe.log_error(f"Simple QR checkin error: {str(e)}")
        return {"status": "error", "message": _("체크인에 실패했습니다")}


def get_location_checklists(work_location, worker):
    """작업장소의 체크리스트 템플릿들을 가져와서 체크리스트 생성"""
    location_doc = frappe.get_doc("Work Site", work_location)
    checklists = []
    
    for template_row in location_doc.work_templates:
        template_doc = frappe.get_doc("Work Template", template_row.work_template)
        
        # 오늘 이미 생성된 체크리스트가 있는지 확인
        existing_checklist = frappe.db.exists("Work Checklist", {
            "work_site": work_location,
            "assigned_to": worker,
            "checklist_template": template_doc.name,
            "due_date": getdate()
        })
        
        if existing_checklist:
            checklist_doc = frappe.get_doc("Work Checklist", existing_checklist)
        else:
            # 새로운 체크리스트 생성
            checklist_doc = create_checklist_from_template(
                template_doc, work_location, worker
            )
        
        # 체크리스트 항목들 가져오기
        items = []
        for item in checklist_doc.checklist_items:
            items.append({
                "idx": item.idx,
                "item_name": item.item_name,
                "is_mandatory": item.is_mandatory,
                "is_completed": item.is_completed,
                "completion_date": item.completion_date
            })
        
        checklists.append({
            "checklist_id": checklist_doc.name,
            "template_name": template_doc.template_name,
            "category": template_doc.category,
            "estimated_minutes": template_doc.estimated_minutes,
            "items": items,
            "completion_percentage": checklist_doc.completion_percentage
        })
    
    return checklists


def create_checklist_from_template(template_doc, work_location, worker):
    """템플릿에서 체크리스트 생성"""
    checklist = frappe.get_doc({
        "doctype": "Work Checklist",
        "checklist_name": f"{template_doc.template_name} - {getdate()}",
        "work_site": work_location,
        "checklist_template": template_doc.name,
        "assigned_to": worker,
        "due_date": getdate(),
        "status": "Pending",
        "checklist_type": template_doc.category,
        "estimated_hours": template_doc.estimated_minutes / 60 if template_doc.estimated_minutes else 0
    })
    
    # 템플릿 항목들을 체크리스트 항목으로 복사
    for template_item in template_doc.checklist_items:
        checklist.append("checklist_items", {
            "item_name": template_item.item_name,
            "is_mandatory": template_item.is_mandatory,
            "is_completed": 0
        })
    
    checklist.insert()
    return checklist


@frappe.whitelist()
def update_checklist_item(checklist_id, item_idx, is_completed, notes=None):
    """체크리스트 항목 업데이트"""
    try:
        checklist = frappe.get_doc("Work Checklist", checklist_id)
        
        # 권한 확인
        if checklist.assigned_to != frappe.session.user:
            return {"status": "error", "message": _("권한이 없습니다")}
        
        item_idx = int(item_idx) - 1  # 1-based to 0-based
        if item_idx >= len(checklist.checklist_items):
            return {"status": "error", "message": _("잘못된 항목입니다")}
        
        item = checklist.checklist_items[item_idx]
        item.is_completed = int(is_completed)
        if is_completed:
            item.completion_date = now()
        else:
            item.completion_date = None
            
        if notes:
            item.notes = notes
        
        # 완료율 계산
        total_items = len(checklist.checklist_items)
        completed_items = sum(1 for item in checklist.checklist_items if item.is_completed)
        checklist.completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
        
        # 모든 필수 항목이 완료되었는지 확인
        mandatory_items = [item for item in checklist.checklist_items if item.is_mandatory]
        completed_mandatory = [item for item in mandatory_items if item.is_completed]
        
        if len(mandatory_items) == len(completed_mandatory) and checklist.completion_percentage == 100:
            checklist.status = "Completed"
            checklist.completion_date = getdate()
        
        checklist.save()
        
        return {
            "status": "success",
            "message": _("업데이트 완료"),
            "completion_percentage": checklist.completion_percentage,
            "is_completed": checklist.status == "Completed"
        }
        
    except Exception as e:
        frappe.log_error(f"Update checklist item error: {str(e)}")
        return {"status": "error", "message": _("업데이트에 실패했습니다")}


@frappe.whitelist()
def complete_work_and_checkout(worker, work_location, completion_notes=None):
    """작업 완료 및 체크아웃"""
    try:
        # 체크인 정보 찾기
        checkin_name = frappe.db.get_value("Worker Checkin", {
            "worker": worker,
            "work_site": work_location,
            "checkin_date": getdate(),
            "checkout_time": ["is", "not set"]
        })
        
        if not checkin_name:
            return {"status": "error", "message": _("체크인 정보를 찾을 수 없습니다")}
        
        # 체크아웃 처리
        checkin = frappe.get_doc("Worker Checkin", checkin_name)
        checkin.checkout_time = now().split()[1]
        checkin.status = "Checked Out"
        
        # 근무시간 계산
        from frappe.utils import time_diff_in_hours
        if checkin.checkin_time and checkin.checkout_time:
            checkin.work_hours = time_diff_in_hours(
                f"{checkin.checkin_date} {checkin.checkout_time}",
                f"{checkin.checkin_date} {checkin.checkin_time}"
            )
        
        checkin.save()
        
        # 작업 보고서 자동 생성
        report = create_simple_work_report(work_location, worker, completion_notes)
        
        return {
            "status": "success",
            "message": _("작업 완료 및 체크아웃 완료"),
            "work_hours": checkin.work_hours,
            "report_id": report.name if report else None
        }
        
    except Exception as e:
        frappe.log_error(f"Complete work and checkout error: {str(e)}")
        return {"status": "error", "message": _("체크아웃에 실패했습니다")}


def create_simple_work_report(work_location, worker, completion_notes=None):
    """간단한 작업 보고서 생성"""
    try:
        location_doc = frappe.get_doc("Work Site", work_location)
        
        # 오늘 완료된 체크리스트들 가져오기
        completed_checklists = frappe.get_all("Work Checklist", {
            "work_site": work_location,
            "assigned_to": worker,
            "due_date": getdate(),
            "status": "Completed"
        }, ["name", "checklist_name", "completion_percentage"])
        
        # 근무시간 가져오기
        work_hours = frappe.db.get_value("Worker Checkin", {
            "worker": worker,
            "work_site": work_location,
            "checkin_date": getdate()
        }, "work_hours") or 0
        
        # 보고서 생성
        report = frappe.get_doc({
            "doctype": "Work Report",
            "report_title": f"{location_doc.site_name} 작업 보고서 - {getdate()}",
            "work_site": work_location,
            "report_date": getdate(),
            "prepared_by": worker,
            "status": "Draft",
            "work_summary": f"총 {len(completed_checklists)}개 작업 완료",
            "total_work_hours": work_hours,
            "worker_comments": completion_notes or ""
        })
        
        # 완료된 체크리스트 정보 추가
        for checklist in completed_checklists:
            report.append("completed_checklists", {
                "checklist": checklist.name,
                "checklist_name": checklist.checklist_name,
                "completion_percentage": checklist.completion_percentage
            })
        
        report.insert()
        report.submit()  # 자동 제출
        
        return report
        
    except Exception as e:
        frappe.log_error(f"Create simple work report error: {str(e)}")
        return None
