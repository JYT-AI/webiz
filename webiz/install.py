# Copyright (c) 2025, WeBiz and contributors
# For license information, please see license.txt

import frappe
from webiz.webiz.custom.warehouse import (
    setup_warehouse_custom_fields,
    setup_project_custom_fields
)


def after_install():
    """WeBiz 앱 설치 후 실행되는 함수"""
    try:
        # Warehouse를 사이트 관리용으로 확장
        setup_warehouse_custom_fields()
        setup_project_custom_fields()
        
        frappe.db.commit()
        print("WeBiz 사이트 관리 설정이 완료되었습니다.")
        
    except Exception as e:
        frappe.log_error(f"WeBiz 설치 중 오류 발생: {str(e)}")
        print(f"설치 중 오류가 발생했습니다: {str(e)}")
