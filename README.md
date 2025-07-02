# WeBiz FM System

시설환경관리(Facility Management) 업무 통합 관리 시스템 for ERPNext

## 📋 개요

WeBiz는 ERPNext 기반의 시설환경관리(FM) 전문 앱으로, 고객 사이트 관리부터 청구까지 FM 업무 전 과정을 체계적으로 관리할 수 있는 통합 솔루션입니다.

## 🏢 주요 기능

### 업무 영역별 Workspace

1. **고객관리** - 영업 파이프라인, 고객 정보, 커뮤니케이션
2. **견적관리** - 견적 프로세스, 품목 관리, 가격 관리, 배송 관리
3. **계약관리** - 계약 프로세스, 공급업체 관리, 구매 관리, 서비스 계약
4. **프로젝트관리** - 프로젝트 관리, 작업 관리, 시간 관리, 이슈 관리
5. **청구관리** - 청구 프로세스, 수금 관리, 정기 청구, 세금 관리
6. **문서관리** - 파일 관리, 커뮤니케이션, 템플릿 관리, 지식 관리

### 사이트 관리 기능

- **Warehouse 확장**: 기존 ERPNext Warehouse를 사이트 관리용으로 확장
- **고객별 사이트 관리**: 고객과 연결된 사이트 정보 체계적 관리
- **프로젝트-사이트 연결**: 프로젝트와 사이트 간 연결 관리
- **사이트 상세 정보**: 면적, 층수, 계약 기간, 관리자 정보 등

## 🚀 설치 방법

### 1. 앱 다운로드
```bash
cd frappe-bench
bench get-app https://github.com/JYT-AI/webiz.git
```

### 2. 사이트에 설치
```bash
bench --site [your-site] install-app webiz
```

### 3. 마이그레이션 실행
```bash
bench --site [your-site] migrate
```

## 📁 프로젝트 구조

```
webiz/
├── webiz/
│   ├── api/                    # API 엔드포인트
│   ├── custom/                 # Custom Fields 및 확장
│   │   └── warehouse.py        # Warehouse 사이트 관리 확장
│   └── workspace/              # 업무 영역별 Workspace
│       ├── 고객관리/
│       ├── 견적관리/
│       ├── 계약관리/
│       ├── 프로젝트관리/
│       ├── 청구관리/
│       └── 문서관리/
├── hooks.py                    # Frappe Hooks 설정
├── install.py                  # 설치 후 초기화
└── README.md
```

## 🔧 기술 스택

- **Framework**: Frappe Framework
- **Base App**: ERPNext
- **Language**: Python, JavaScript
- **Database**: MariaDB/PostgreSQL

## 📊 사이트 관리 Custom Fields

### Warehouse 확장 필드

- `is_site`: 사이트로 사용 여부
- `site_customer`: 연결된 고객
- `site_manager`: 사이트 관리자
- `site_type`: 사이트 유형 (오피스/공장/창고/매장/기타)
- `site_area`: 면적 (㎡)
- `site_floors`: 층수
- `site_contract_start/end`: 계약 기간
- `site_notes`: 사이트 메모

### Project 확장 필드

- `site`: 연결된 사이트 (Link to Warehouse)
- `site_manager`: 사이트 관리자 (자동 가져오기)

## 🎯 사용 방법

### 사이트 생성
1. Warehouse 리스트에서 새 창고 생성
2. "사이트로 사용" 체크박스 활성화
3. 고객, 관리자, 유형 등 사이트 정보 입력

### 프로젝트에서 사이트 연결
1. Project 생성/수정 시 사이트 정보 섹션에서 사이트 선택
2. 사이트 관리자 정보 자동 표시

## 🤝 기여하기

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/webiz
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

Proprietary

## 📞 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/JYT-AI/webiz/issues)
- **문의**: ktk@jyt.ai

## 🏗️ 개발 상태

- ✅ 기본 Workspace 구성
- ✅ 사이트 관리 기능 (Warehouse 확장)
- ✅ 프로젝트-사이트 연결
- 🚧 고급 보고서 기능
- 🚧 모바일 최적화
- 📋 API 문서화

---

**WeBiz FM System** - 시설환경관리의 새로운 표준
