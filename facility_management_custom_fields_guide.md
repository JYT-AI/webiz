# 시설 관리 시스템 사용자 정의 필드 추가 가이드

## 📋 개요

이 가이드는 Frappe/ERPNext에서 완전한 시설 관리 시스템을 구축하기 위한 사용자 정의 필드 추가 방법을 제공합니다.

## 🎯 전체 시스템 구조

```
Project (시설 관리 계약)
├── Customer Site (작업 장소들)
├── Task (작업 마스터 템플릿들)
│   ├── Facility Checklist Template 연결
│   └── Employee 할당
└── Auto Repeat → 매일 Timesheet 자동 생성
    └── Timesheet (일일 작업 실행)
        ├── Timesheet Checklist Result (체크리스트 수행 결과)
        ├── 시간 추적 (자동)
        ├── 완료 사진
        └── 품질 평가
```

## 🔧 사용자 정의 필드 추가 방법

### 기본 접근 방법
1. Frappe 데스크에서 "Customize Form" 검색
2. 또는 직접 URL: `http://your-site/app/customize-form`
3. DocType 선택 후 "Add Row" 버튼으로 필드 추가
4. 필드 정보 입력 후 "Update" 버튼 클릭

---

## 1️⃣ Project DocType 사용자 정의 필드

**접근:** Customize Form → DocType: "Project" 선택

### 시설 관리 정보 섹션 (project_type 다음에 추가)

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `facility_management_section` | Section Break | 시설 관리 정보 | Collapsible: ✅ |
| `contract_type` | Select | 계약 유형 | 시설관리<br>청소<br>보안<br>유지보수<br>종합관리 |
| `service_frequency` | Select | 서비스 주기 | 일간<br>주간 (평일만)<br>주간 (전체)<br>월간<br>분기 |
| `column_break_facility` | Column Break | - | - |
| `contract_start_date` | Date | 계약 시작일 | - |
| `contract_end_date` | Date | 계약 종료일 | - |
| `primary_contact_person` | Data | 주 담당자 | - |
| `billing_cycle` | Select | 청구 주기 | 월간<br>분기<br>반기<br>연간 |

---

## 2️⃣ Task DocType 사용자 정의 필드

**접근:** Customize Form → DocType: "Task" 선택

### 시설 작업 정보 섹션 (project 다음에 추가)

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `facility_work_section` | Section Break | 시설 작업 정보 | - |
| `customer_site` | Link | 작업 사이트 | Options: Customer Site |
| `checklist_template` | Link | 체크리스트 템플릿 | Options: Facility Checklist Template |
| `assigned_employee` | Link | 담당 직원 | Options: Employee |
| `column_break_work` | Column Break | - | - |
| `work_type` | Select | 작업 유형 | 일회성<br>일간<br>주간<br>월간<br>정기점검 |
| `scheduled_start_time` | Datetime | 예정 시작 시간 | - |
| `estimated_duration` | Float | 예상 소요시간 (시간) | Precision: 2 |

### 작업 실행 정보 섹션

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `work_execution_section` | Section Break | 작업 실행 정보 | Collapsible: ✅ |
| `actual_start_time` | Datetime | 실제 시작 시간 | - |
| `actual_end_time` | Datetime | 실제 종료 시간 | - |
| `work_status` | Select | 작업 상태 | 예정<br>진행중<br>완료<br>취소<br>보류<br>Default: 예정 |
| `column_break_execution` | Column Break | - | - |
| `completion_photos` | Attach | 완료 사진 | - |
| `quality_rating` | Select | 품질 평가 | 1<br>2<br>3<br>4<br>5 |
| `customer_feedback` | Text | 고객 피드백 | - |

---

## 3️⃣ Timesheet DocType 사용자 정의 필드

**접근:** Customize Form → DocType: "Timesheet" 선택

### 시설 작업 정보 섹션 (employee 다음에 추가)

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `facility_work_section` | Section Break | 시설 작업 정보 | - |
| `customer_site` | Link | 작업 사이트 | Options: Customer Site |
| `checklist_template` | Link | 체크리스트 템플릿 | Options: Facility Checklist Template |
| `related_task` | Link | 관련 Task | Options: Task |
| `column_break_timesheet` | Column Break | - | - |
| `work_date` | Date | 작업 날짜 | Default: Today |
| `work_status` | Select | 작업 상태 | 시작 전<br>진행 중<br>완료<br>부분 완료<br>취소<br>Default: 시작 전 |
| `quality_rating` | Select | 품질 평가 | 1<br>2<br>3<br>4<br>5 |

### 체크리스트 수행 결과 섹션

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `checklist_section` | Section Break | 체크리스트 수행 결과 | - |
| `checklist_results` | Table | 체크리스트 결과 | Options: Timesheet Checklist Result |

### 작업 완료 정보 섹션

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `completion_section` | Section Break | 작업 완료 정보 | Collapsible: ✅ |
| `completion_photos` | Attach | 완료 사진 | - |
| `customer_feedback` | Text | 고객 피드백 | - |
| `column_break_completion` | Column Break | - | - |
| `special_notes` | Text | 특이사항 | - |
| `next_recommendations` | Text | 다음 작업 권장사항 | - |
| `customer_signature` | Attach | 고객 서명 (선택사항) | - |

---

## 4️⃣ Employee DocType 사용자 정의 필드

**접근:** Customize Form → DocType: "Employee" 선택

### 시설 관리 정보 섹션 (personal_details 섹션 다음에 추가)

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `facility_management_section` | Section Break | 시설 관리 정보 | Collapsible: ✅ |
| `facility_skills` | Text | 시설 관리 기술 | Description: 청소, 보안, 전기, 배관 등 |
| `certification_info` | Text | 자격증 정보 | - |
| `column_break_facility_emp` | Column Break | - | - |
| `mobile_device_id` | Data | 모바일 기기 ID | - |
| `emergency_contact` | Data | 비상 연락처 | Options: Phone |
| `work_areas` | Text | 작업 가능 지역 | - |

---

## 5️⃣ Attendance DocType 사용자 정의 필드

**접근:** Customize Form → DocType: "Attendance" 선택

### 현장 근태 정보 섹션 (attendance_date 다음에 추가)

| 필드명 | 필드 타입 | 라벨 | 옵션/설정 |
|--------|-----------|------|-----------|
| `field_attendance_section` | Section Break | 현장 근태 정보 | Collapsible: ✅ |
| `check_in_location` | Data | 체크인 위치 (GPS) | - |
| `check_out_location` | Data | 체크아웃 위치 (GPS) | - |
| `work_site` | Link | 작업 현장 | Options: Customer Site |
| `column_break_attendance` | Column Break | - | - |
| `check_in_photo` | Attach | 출근 인증 사진 | - |
| `check_out_photo` | Attach | 퇴근 인증 사진 | - |
| `site_notes` | Text | 현장 특이사항 | - |

---

## 🔄 반복 작업 설정 프로세스

### A. 마스터 Task 생성

1. **Task → 새로 만들기**
2. **정보 입력:**
   - Subject: `[템플릿] ABC회사 일일 청소`
   - Project: 해당 프로젝트 선택
   - 작업 사이트: ABC회사 본사
   - 체크리스트 템플릿: Office Cleaning Standard
   - 담당 직원: 김청소
   - 작업 유형: "일간" 선택
   - 예정 시작 시간: 08:00
3. **저장** (Draft 상태로 유지)

### B. 마스터 Timesheet 생성

1. **Timesheet → 새로 만들기**
2. **정보 입력:**
   - Employee: 김청소
   - 작업 사이트: ABC회사 본사
   - 체크리스트 템플릿: Office Cleaning Standard
   - 관련 Task: 위에서 만든 마스터 Task
   - 작업 날짜: 오늘 날짜
3. **저장** (Draft 상태로 유지)

### C. Auto Repeat 설정

1. **Auto Repeat → 새로 만들기**
2. **설정:**
   - Reference DocType: `Timesheet`
   - Reference Document: 위에서 만든 마스터 Timesheet
   - Frequency: `Daily`
   - Start Date: 계약 시작일
   - End Date: 계약 종료일
   - Repeat on Days: 월,화,수,목,금 선택 (평일만)
   - Submit on Creation: ❌ (Draft로 생성)
3. **저장 및 Submit**

---

## 📊 완성된 시스템 기능

### 👨‍💼 관리자 기능
- ✅ 프로젝트별 계약 관리
- ✅ 작업 템플릿 생성 및 자동 반복 설정
- ✅ 실시간 작업 현황 모니터링
- ✅ 자동 보고서 생성
- ✅ 품질 평가 및 트렌드 분석

### 👷‍♂️ 작업자 기능
- ✅ 자동 생성된 Timesheet에서 작업 수행
- ✅ 체크리스트 항목별 상세 기록
- ✅ GPS 기반 출퇴근 관리
- ✅ 사진 첨부 및 품질 평가
- ✅ 자동 시간 추적

### 🏢 고객 기능
- ✅ 일일 작업 완료 보고서 수신
- ✅ 작업 품질 및 시간 투명성 확보
- ✅ 실시간 작업 현황 확인

---

## ⚠️ 주의사항

1. **필드 추가 순서**: 반드시 위에서 제시한 순서대로 추가하세요.
2. **필드명 정확성**: 필드명(fieldname)은 정확히 입력하세요.
3. **마이그레이션**: 모든 필드 추가 후 `bench migrate` 실행 권장.
4. **권한 설정**: 필요에 따라 역할별 필드 접근 권한 설정.
5. **테스트**: 각 단계별로 기능 테스트 수행.

---

## 📱 워크스페이스 구성

### 작업자 전용
- 내 작업 목록 (Task)
- 내 근태 기록 (Attendance)
- 작업 시간 기록 (Timesheet)
- 작업 사이트 정보 (Customer Site)

### 관리자 전용
- 프로젝트 관리 (Project)
- 작업 배정 관리 (Task)
- 체크리스트 템플릿 (Facility Checklist Template)
- 직원 관리 (Employee)
- 고객 사이트 관리 (Customer Site)
- 근태 현황 (Attendance)
- 반복 작업 설정 (Auto Repeat)

### 공통 사용
- 고객 정보 (Customer)
- 계약 정보 (Contract)
- 커뮤니케이션 (Communication)

---

## 🎯 실제 운영 시나리오

### 청소 업체 사례
```
프로젝트: "ABC회사 사무실 청소 계약"
├── Auto Repeat 1: 평일 일반 청소 (월-금)
├── Auto Repeat 2: 주말 심화 청소 (토)
└── Auto Repeat 3: 월말 대청소 (매월 마지막 금요일)
```

### 보안 업체 사례
```
프로젝트: "XYZ빌딩 보안 서비스"
├── Auto Repeat 1: 일일 순찰 (매일)
├── Auto Repeat 2: 주간 점검 (매주 월요일)
└── Auto Repeat 3: 월간 보고서 (매월 1일)
```

---

## 🎉 완료 후 다음 단계

1. **워크스페이스 확인**: 현장관리 워크스페이스에서 모든 DocType 접근 가능
2. **권한 설정**: 역할별 접근 권한 세부 조정
3. **보고서 생성**: 필요한 보고서 및 대시보드 구성
4. **모바일 최적화**: 모바일 앱에서의 사용성 확인
5. **사용자 교육**: 관리자 및 작업자 대상 교육 실시

---

## 🔧 추가 개발 가능 기능

### 고급 기능
- **AI 기반 작업 최적화**: 작업 패턴 분석 및 최적 스케줄 제안
- **IoT 센서 연동**: 실시간 환경 모니터링
- **모바일 앱 개발**: 전용 모바일 앱 구축
- **고객 포털**: 고객 전용 웹 포털 제공

### 보고서 및 분석
- **실시간 대시보드**: 작업 현황 실시간 모니터링
- **품질 트렌드 분석**: 시간별/지역별 품질 변화 추적
- **비용 분석**: 작업 시간 대비 비용 효율성 분석
- **예측 분석**: 향후 작업량 및 인력 수요 예측

---

**📝 작성일**: 2025-01-15
**🔄 업데이트**: 필요시 지속 업데이트
**📧 문의**: 시스템 관리자에게 연락
