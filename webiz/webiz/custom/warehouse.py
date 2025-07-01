# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_warehouse_custom_fields():
    """사이트 관리를 위한 Warehouse Custom Fields 설정"""
    
    custom_fields = {
        "Warehouse": [
            {
                "fieldname": "site_management_section",
                "label": "사이트 관리",
                "fieldtype": "Section Break",
                "insert_after": "warehouse_type",
                "collapsible": 1
            },
            {
                "fieldname": "is_site",
                "label": "사이트로 사용",
                "fieldtype": "Check",
                "insert_after": "site_management_section",
                "default": 0,
                "description": "이 창고를 고객 사이트로 사용합니다"
            },
            {
                "fieldname": "site_customer",
                "label": "고객",
                "fieldtype": "Link",
                "options": "Customer",
                "insert_after": "is_site",
                "depends_on": "is_site",
                "description": "이 사이트의 고객을 선택하세요"
            },
            {
                "fieldname": "site_column_break",
                "fieldtype": "Column Break",
                "insert_after": "site_customer"
            },
            {
                "fieldname": "site_manager",
                "label": "사이트 관리자",
                "fieldtype": "Data",
                "insert_after": "site_column_break",
                "depends_on": "is_site",
                "description": "사이트 현장 관리자 이름"
            },
            {
                "fieldname": "site_type",
                "label": "사이트 유형",
                "fieldtype": "Select",
                "options": "\n오피스\n공장\n창고\n매장\n기타",
                "insert_after": "site_manager",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_details_section",
                "label": "사이트 상세 정보",
                "fieldtype": "Section Break",
                "insert_after": "site_type",
                "depends_on": "is_site",
                "collapsible": 1
            },
            {
                "fieldname": "site_area",
                "label": "면적 (㎡)",
                "fieldtype": "Float",
                "insert_after": "site_details_section",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_floors",
                "label": "층수",
                "fieldtype": "Int",
                "insert_after": "site_area",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_column_break_2",
                "fieldtype": "Column Break",
                "insert_after": "site_floors"
            },
            {
                "fieldname": "site_established_date",
                "label": "설립일",
                "fieldtype": "Date",
                "insert_after": "site_column_break_2",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_contract_start",
                "label": "계약 시작일",
                "fieldtype": "Date",
                "insert_after": "site_established_date",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_contract_end",
                "label": "계약 종료일",
                "fieldtype": "Date",
                "insert_after": "site_contract_start",
                "depends_on": "is_site"
            },
            {
                "fieldname": "site_notes_section",
                "label": "사이트 메모",
                "fieldtype": "Section Break",
                "insert_after": "site_contract_end",
                "depends_on": "is_site",
                "collapsible": 1
            },
            {
                "fieldname": "site_notes",
                "label": "메모",
                "fieldtype": "Text Editor",
                "insert_after": "site_notes_section",
                "depends_on": "is_site",
                "description": "사이트 관련 특이사항이나 메모를 입력하세요"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()


def validate_warehouse_site(doc, method):
    """Warehouse 문서 검증 - 사이트 관련 필드 검증"""
    if doc.get("is_site"):
        # 사이트로 사용할 경우 고객 필수
        if not doc.get("site_customer"):
            frappe.throw("사이트로 사용하려면 고객을 선택해야 합니다.")

        # 계약 종료일이 시작일보다 이전일 수 없음
        if doc.get("site_contract_start") and doc.get("site_contract_end"):
            if doc.site_contract_end < doc.site_contract_start:
                frappe.throw("계약 종료일은 시작일보다 이후여야 합니다.")


def setup_project_custom_fields():
    """Project DocType에 사이트 연결 필드 추가"""
    
    custom_fields = {
        "Project": [
            {
                "fieldname": "site_info_section",
                "label": "사이트 정보",
                "fieldtype": "Section Break",
                "insert_after": "project_type",
                "collapsible": 1
            },
            {
                "fieldname": "site",
                "label": "사이트",
                "fieldtype": "Link",
                "options": "Warehouse",
                "insert_after": "site_info_section",
                "description": "이 프로젝트가 진행될 사이트를 선택하세요"
            },
            {
                "fieldname": "site_column_break",
                "fieldtype": "Column Break",
                "insert_after": "site"
            },
            {
                "fieldname": "site_manager",
                "label": "사이트 관리자",
                "fieldtype": "Data",
                "insert_after": "site_column_break",
                "read_only": 1,
                "fetch_from": "site.site_manager",
                "description": "선택된 사이트의 관리자"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
