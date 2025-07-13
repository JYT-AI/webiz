# 🔌 현장관리 시스템 API 문서

## 📋 개요

webiz 현장관리 시스템의 REST API 문서입니다. 외부 시스템과의 연동 및 모바일 앱 개발을 위한 API 엔드포인트를 제공합니다.

### 기본 정보
- **Base URL**: `https://your-domain.com/api/resource/`
- **인증 방식**: API Key 또는 Token 기반
- **데이터 형식**: JSON
- **HTTP 메서드**: GET, POST, PUT, DELETE

---

## 🔐 인증

### API Key 방식
```http
GET /api/resource/Work Session
Authorization: token {api_key}:{api_secret}
```

### Token 방식
```http
POST /api/method/login
Content-Type: application/json

{
    "usr": "user@example.com",
    "pwd": "password"
}
```

---

## 📊 Work Session API

### 1. 작업 목록 조회
```http
GET /api/resource/Work Session
```

**Query Parameters:**
- `filters`: JSON 형태의 필터 조건
- `fields`: 반환할 필드 목록
- `limit_start`: 페이징 시작 위치
- `limit_page_length`: 페이지당 항목 수

**Example:**
```http
GET /api/resource/Work Session?filters=[["assigned_employee","=","EMP-001"]]&fields=["name","title","status","work_date"]
```

**Response:**
```json
{
    "data": [
        {
            "name": "WS-2025-001",
            "title": "ABC 회사 청소 작업 - 2025-07-13",
            "status": "Scheduled",
            "work_date": "2025-07-13"
        }
    ]
}
```

### 2. 작업 상세 조회
```http
GET /api/resource/Work Session/{name}
```

**Response:**
```json
{
    "data": {
        "name": "WS-2025-001",
        "title": "ABC 회사 청소 작업 - 2025-07-13",
        "status": "Scheduled",
        "work_date": "2025-07-13",
        "assigned_employee": "EMP-001",
        "customer_site": "SITE-001",
        "checklist_results": [
            {
                "checklist_item": "화장실 청소",
                "status": "Pending",
                "is_mandatory": 1
            }
        ]
    }
}
```

### 3. 작업 시작
```http
POST /api/method/webiz.webiz.doctype.work_session.work_session.start_work
Content-Type: application/json

{
    "work_session": "WS-2025-001",
    "check_in_location": "37.5665,126.9780"
}
```

**Response:**
```json
{
    "message": "작업이 시작되었습니다."
}
```

### 4. 작업 완료
```http
POST /api/method/webiz.webiz.doctype.work_session.work_session.complete_work
Content-Type: application/json

{
    "work_session": "WS-2025-001",
    "check_out_location": "37.5665,126.9780"
}
```

### 5. 체크리스트 업데이트
```http
POST /api/method/webiz.webiz.doctype.work_session.work_session.update_checklist_item
Content-Type: application/json

{
    "work_session": "WS-2025-001",
    "item_name": "화장실 청소",
    "status": "Completed",
    "notes": "정상 완료",
    "photo": "/files/photo.jpg"
}
```

---

## 👷 Work Employee API

### 1. 작업자 목록 조회
```http
GET /api/resource/Work Employee
```

### 2. 작업자 스케줄 조회
```http
POST /api/method/webiz.webiz.doctype.work_employee.work_employee.get_schedule
Content-Type: application/json

{
    "employee": "WE-2025-001",
    "start_date": "2025-07-13",
    "end_date": "2025-07-19"
}
```

**Response:**
```json
{
    "message": [
        {
            "session_name": "WS-2025-001",
            "date": "2025-07-13",
            "start_time": "09:00:00",
            "site": "ABC 회사",
            "task": "일반 청소",
            "status": "Scheduled",
            "duration": 4.0
        }
    ]
}
```

---

## 🏢 Work Attendance API

### 1. 체크인
```http
POST /api/method/webiz.webiz.doctype.work_attendance.work_attendance.check_in
Content-Type: application/json

{
    "attendance": "WA-2025-001",
    "location": "37.5665,126.9780",
    "photo": "/files/checkin_photo.jpg",
    "device_info": "iPhone 12 Pro"
}
```

### 2. 체크아웃
```http
POST /api/method/webiz.webiz.doctype.work_attendance.work_attendance.check_out
Content-Type: application/json

{
    "attendance": "WA-2025-001",
    "location": "37.5665,126.9780",
    "photo": "/files/checkout_photo.jpg"
}
```

### 3. 출입 기록 조회
```http
GET /api/resource/Work Attendance?filters=[["employee","=","EMP-001"],["attendance_date","=","2025-07-13"]]
```

---

## 📱 모바일 최적화 API

### 1. 모바일 작업 데이터 조회
```http
POST /api/method/webiz.webiz.doctype.work_session.work_session.get_mobile_view_data
Content-Type: application/json

{
    "work_session": "WS-2025-001"
}
```

**Response:**
```json
{
    "message": {
        "session_info": {
            "name": "WS-2025-001",
            "title": "ABC 회사 청소 작업",
            "status": "In Progress",
            "work_date": "2025-07-13",
            "site_name": "ABC 회사 본사",
            "estimated_duration": 4.0
        },
        "checklist": [
            {
                "item": "화장실 청소",
                "description": "모든 화장실 청소 및 소독",
                "is_mandatory": true,
                "status": "Completed",
                "notes": "정상 완료"
            }
        ],
        "completion_percentage": 75
    }
}
```

### 2. 모바일 출입 요약
```http
POST /api/method/webiz.webiz.doctype.work_attendance.work_attendance.get_mobile_summary
Content-Type: application/json

{
    "attendance": "WA-2025-001"
}
```

---

## 📊 보고서 API

### 1. 작업자 성과 조회
```http
POST /api/method/webiz.webiz.doctype.work_employee.work_employee.get_workload_for_period
Content-Type: application/json

{
    "employee": "WE-2025-001",
    "start_date": "2025-07-01",
    "end_date": "2025-07-31"
}
```

**Response:**
```json
{
    "message": {
        "total_sessions": 20,
        "completed_sessions": 18,
        "total_hours": 72.5,
        "average_rating": 4.2
    }
}
```

---

## 🔄 Webhook 이벤트

### 지원 이벤트
- `work_session.started`: 작업 시작 시
- `work_session.completed`: 작업 완료 시
- `work_attendance.checked_in`: 체크인 시
- `work_attendance.checked_out`: 체크아웃 시

### Webhook 설정
```http
POST /api/resource/Webhook
Content-Type: application/json

{
    "webhook_doctype": "Work Session",
    "webhook_docevent": "on_update",
    "request_url": "https://your-app.com/webhook",
    "request_structure": "Form URL-Encoded"
}
```

---

## ❌ 에러 코드

| 코드 | 메시지 | 설명 |
|------|--------|------|
| 400 | Bad Request | 잘못된 요청 형식 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 409 | Conflict | 중복 데이터 |
| 500 | Internal Server Error | 서버 오류 |

### 에러 응답 형식
```json
{
    "exc_type": "ValidationError",
    "exception": "작업이 이미 시작되었습니다.",
    "httpStatus": 400
}
```

---

## 📝 SDK 및 예제

### JavaScript SDK
```javascript
// webiz-sdk.js
class WebizAPI {
    constructor(baseUrl, apiKey, apiSecret) {
        this.baseUrl = baseUrl;
        this.auth = btoa(`${apiKey}:${apiSecret}`);
    }
    
    async getWorkSessions(employeeId) {
        const response = await fetch(`${this.baseUrl}/api/resource/Work Session?filters=[["assigned_employee","=","${employeeId}"]]`, {
            headers: {
                'Authorization': `Basic ${this.auth}`
            }
        });
        return response.json();
    }
    
    async startWork(sessionId, location) {
        const response = await fetch(`${this.baseUrl}/api/method/webiz.webiz.doctype.work_session.work_session.start_work`, {
            method: 'POST',
            headers: {
                'Authorization': `Basic ${this.auth}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                work_session: sessionId,
                check_in_location: location
            })
        });
        return response.json();
    }
}
```

### Python SDK
```python
import requests
import base64

class WebizAPI:
    def __init__(self, base_url, api_key, api_secret):
        self.base_url = base_url
        self.auth = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    
    def get_work_sessions(self, employee_id):
        url = f"{self.base_url}/api/resource/Work Session"
        params = {
            'filters': f'[["assigned_employee","=","{employee_id}"]]'
        }
        headers = {'Authorization': f'Basic {self.auth}'}
        
        response = requests.get(url, params=params, headers=headers)
        return response.json()
```

---

**📝 문서 버전**: v1.0  
**📅 최종 업데이트**: 2025-07-13  
**✍️ 작성자**: webiz 개발팀
