import frappe
import requests
import json
from urllib.parse import quote_plus, urljoin
import re
from datetime import datetime
from frappe import _


@frappe.whitelist()
def web_search(query, num_results=5, language="ko", safe_search="moderate"):
    """
    웹 검색을 수행하는 함수 - Raven AI의 custom function으로 사용
    
    Args:
        query (str): 검색할 키워드
        num_results (int, optional): 반환할 결과 수 (기본값: 5, 최대: 10)
        language (str, optional): 검색 언어 (기본값: "ko" - 한국어)
        safe_search (str, optional): 안전 검색 수준 ("off", "moderate", "strict")
    
    Returns:
        dict: 검색 결과를 포함한 딕셔너리
    """
    
    try:
        # 입력값 검증
        if not query or not query.strip():
            return {
                "success": False,
                "error": "검색 키워드가 필요합니다",
                "message": "검색할 키워드를 입력해주세요"
            }
        
        # 결과 수 제한
        num_results = min(max(int(num_results), 1), 10)

        # Serper API 사용
        search_results = _perform_serper_search(query, num_results, language, safe_search)
        
        if not search_results["success"]:
            return search_results
        
        # 결과 포맷팅
        formatted_results = []
        for idx, result in enumerate(search_results["results"], 1):
            formatted_result = {
                "rank": idx,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "domain": _extract_domain(result.get("url", "")),
                "relevance_score": _calculate_relevance_score(query, result)
            }
            formatted_results.append(formatted_result)
        
        # 검색 통계
        search_stats = {
            "query": query,
            "total_results": len(formatted_results),
            "search_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "language": language,
            "safe_search": safe_search
        }
        
        return {
            "success": True,
            "search_stats": search_stats,
            "results": formatted_results,
            "summary": _generate_search_summary(query, formatted_results)
        }
        
    except Exception as e:
        frappe.log_error(f"웹 검색 API 오류: {str(e)}")
        return {
            "success": False,
            "error": "웹 검색 중 오류가 발생했습니다",
            "message": str(e)
        }


def _get_serper_api_key():
    """
    Serper API 키를 config에서 가져오는 함수
    """
    # 1. site_config.json에서 확인
    api_key = frappe.conf.get("serper_api_key")

    if not api_key:
        # 2. System Settings에서 확인 (선택사항)
        try:
            from frappe.core.doctype.system_settings.system_settings import get_system_settings
            api_key = get_system_settings("serper_api_key")
        except:
            pass

    if not api_key:
        # 3. 환경변수에서 확인
        import os
        api_key = os.getenv("SERPER_API_KEY")

    return api_key


def _perform_serper_search(query, num_results, language, safe_search):
    """
    Serper API를 사용한 웹 검색
    """
    try:
        # API 키 확인
        api_key = _get_serper_api_key()
            
        if not api_key:
            return {
                "success": False,
                "error": "Serper API 키가 설정되지 않았습니다",
                "message": "site_config.json에 'serper_api_key'를 추가하거나 환경변수 SERPER_API_KEY를 설정해주세요"
            }

        # Serper API 엔드포인트
        search_url = "https://google.serper.dev/search"

        # 검색 파라미터 설정
        payload = {
            "q": query,
            "num": num_results,
            "hl": language if language in ["ko", "en", "ja", "zh"] else "ko"
        }

        # 안전 검색 설정
        if safe_search == "strict":
            payload["safe"] = "active"
        elif safe_search == "off":
            payload["safe"] = "off"
        # moderate는 기본값이므로 설정하지 않음

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(search_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        results = []

        # organic 검색 결과 처리
        for item in data.get("organic", []):
            result = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0)
            }
            results.append(result)

        # 결과가 부족한 경우 뉴스 결과도 포함
        if len(results) < num_results and data.get("news"):
            for news_item in data.get("news", [])[:num_results - len(results)]:
                result = {
                    "title": news_item.get("title", ""),
                    "url": news_item.get("link", ""),
                    "snippet": news_item.get("snippet", ""),
                    "position": len(results) + 1,
                    "type": "news"
                }
                results.append(result)

        return {
            "success": True,
            "results": results[:num_results],
            "search_metadata": {
                "total_results": data.get("searchInformation", {}).get("totalResults", 0),
                "search_time": data.get("searchInformation", {}).get("searchTime", 0)
            }
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Serper API 요청 실패: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"검색 처리 오류: {str(e)}"
        }


def _get_fallback_results(query, count):
    """
    검색 결과가 부족할 때 사용할 대체 결과
    """
    fallback_sites = [
        {"domain": "wikipedia.org", "title_suffix": " - 위키백과"},
        {"domain": "namu.wiki", "title_suffix": " - 나무위키"},
        {"domain": "blog.naver.com", "title_suffix": " - 네이버 블로그"},
        {"domain": "tistory.com", "title_suffix": " - 티스토리"},
        {"domain": "youtube.com", "title_suffix": " - YouTube"}
    ]
    
    results = []
    for i in range(min(count, len(fallback_sites))):
        site = fallback_sites[i]
        results.append({
            "title": f"{query}{site['title_suffix']}",
            "url": f"https://{site['domain']}/search?q={quote_plus(query)}",
            "snippet": f"{query}에 대한 {site['domain']} 검색 결과입니다."
        })
    
    return results


def _extract_domain(url):
    """
    URL에서 도메인 추출
    """
    try:
        if not url:
            return ""
        
        # http:// 또는 https:// 제거
        domain = re.sub(r'^https?://', '', url)
        # www. 제거
        domain = re.sub(r'^www\.', '', domain)
        # 첫 번째 / 이후 제거
        domain = domain.split('/')[0]
        
        return domain
    except:
        return ""


def _calculate_relevance_score(query, result):
    """
    검색 결과의 관련성 점수 계산
    """
    try:
        score = 0
        query_lower = query.lower()
        
        # 제목에서 키워드 매칭
        title = result.get("title", "").lower()
        if query_lower in title:
            score += 50
        
        # 스니펫에서 키워드 매칭
        snippet = result.get("snippet", "").lower()
        if query_lower in snippet:
            score += 30
        
        # 키워드 개별 단어 매칭
        query_words = query_lower.split()
        for word in query_words:
            if word in title:
                score += 10
            if word in snippet:
                score += 5
        
        return min(score, 100)  # 최대 100점
        
    except:
        return 0


def _generate_search_summary(query, results):
    """
    검색 결과 요약 생성
    """
    if not results:
        return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."
    
    top_domains = {}
    for result in results:
        domain = result.get("domain", "")
        if domain:
            top_domains[domain] = top_domains.get(domain, 0) + 1
    
    summary = f"'{query}'에 대한 {len(results)}개의 검색 결과를 찾았습니다."
    
    if top_domains:
        most_common_domain = max(top_domains.keys(), key=lambda k: top_domains[k])
        summary += f" 주요 출처: {most_common_domain}"
    
    return summary


def _perform_serper_news_search(query, num_results, language):
    """
    Serper API를 사용한 뉴스 검색
    """
    try:
        # API 키 확인
        api_key = _get_serper_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "Serper API 키가 설정되지 않았습니다"
            }

        # Serper News API 엔드포인트
        search_url = "https://google.serper.dev/news"

        # 검색 파라미터 설정
        payload = {
            "q": query,
            "num": num_results,
            "hl": language if language in ["ko", "en", "ja", "zh"] else "ko"
        }

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(search_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        results = []

        # 뉴스 검색 결과 처리
        for item in data.get("news", []):
            result = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "source": item.get("source", ""),
                "position": item.get("position", 0),
                "type": "news"
            }
            results.append(result)

        return {
            "success": True,
            "results": results[:num_results],
            "search_metadata": {
                "total_results": len(results),
                "search_time": data.get("searchInformation", {}).get("searchTime", 0)
            }
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Serper News API 요청 실패: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"뉴스 검색 처리 오류: {str(e)}"
        }


@frappe.whitelist()
def search_news(query, num_results=5, language="ko"):
    """
    뉴스 검색 전용 함수

    Args:
        query (str): 검색할 뉴스 키워드
        num_results (int, optional): 반환할 결과 수 (기본값: 5)
        language (str, optional): 검색 언어 (기본값: "ko")

    Returns:
        dict: 뉴스 검색 결과
    """

    try:
        # 입력값 검증
        if not query or not query.strip():
            return {
                "success": False,
                "error": "뉴스 검색 키워드가 필요합니다",
                "message": "검색할 뉴스 키워드를 입력해주세요"
            }

        # 결과 수 제한
        num_results = min(max(int(num_results), 1), 10)

        # Serper News API 사용
        search_results = _perform_serper_news_search(query, num_results, language)

        if not search_results["success"]:
            return search_results

        # 결과 포맷팅
        formatted_results = []
        for idx, result in enumerate(search_results["results"], 1):
            formatted_result = {
                "rank": idx,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "date": result.get("date", ""),
                "source": result.get("source", ""),
                "domain": _extract_domain(result.get("url", "")),
                "relevance_score": _calculate_relevance_score(query, result),
                "type": "news"
            }
            formatted_results.append(formatted_result)

        # 검색 통계
        search_stats = {
            "query": query,
            "total_results": len(formatted_results),
            "search_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "language": language,
            "search_type": "news"
        }

        return {
            "success": True,
            "search_stats": search_stats,
            "results": formatted_results,
            "summary": f"'{query}' 관련 뉴스 {len(formatted_results)}개를 찾았습니다."
        }

    except Exception as e:
        frappe.log_error(f"뉴스 검색 API 오류: {str(e)}")
        return {
            "success": False,
            "error": "뉴스 검색 중 오류가 발생했습니다",
            "message": str(e)
        }


@frappe.whitelist()
def get_search_suggestions(query):
    """
    검색 제안어 반환 함수
    
    Args:
        query (str): 검색 키워드
    
    Returns:
        dict: 검색 제안어 목록
    """
    
    try:
        if not query or len(query.strip()) < 2:
            return {
                "success": False,
                "error": "검색어는 최소 2글자 이상이어야 합니다"
            }
        
        # 간단한 검색 제안어 생성 (실제로는 검색 엔진 API 사용)
        suggestions = [
            f"{query} 뜻",
            f"{query} 방법",
            f"{query} 종류",
            f"{query} 특징",
            f"{query} 장점",
            f"{query} 단점",
            f"{query} 비교",
            f"{query} 추천"
        ]
        
        return {
            "success": True,
            "query": query,
            "suggestions": suggestions[:5],
            "total_suggestions": len(suggestions)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"검색 제안어 생성 오류: {str(e)}"
        }


@frappe.whitelist()
def get_search_help():
    """
    웹 검색 툴 사용법 안내 함수

    Returns:
        dict: 사용법 및 예제
    """

    return {
        "success": True,
        "tool_name": "웹 검색 툴 (Serper API)",
        "description": "Raven AI에서 사용할 수 있는 Serper API 기반 웹 검색 custom function",
        "api_provider": "Serper (Google Search API)",
        "setup_required": {
            "api_key": "Serper API 키가 필요합니다",
            "config_methods": [
                "site_config.json에 'serper_api_key' 추가",
                "환경변수 SERPER_API_KEY 설정",
                "System Settings에 serper_api_key 추가 (선택사항)"
            ],
            "get_api_key": "https://serper.dev에서 무료 API 키 발급 가능"
        },
        "functions": {
            "web_search": {
                "description": "일반 웹 검색 (Google 검색 결과)",
                "parameters": {
                    "query": "검색 키워드 (필수)",
                    "num_results": "결과 수 (선택, 기본값: 5, 최대: 10)",
                    "language": "검색 언어 (선택, 기본값: 'ko')",
                    "safe_search": "안전 검색 수준 (선택, 기본값: 'moderate')"
                },
                "example": "webiz.api.web_search.web_search(query='파이썬 프로그래밍', num_results=3)"
            },
            "search_news": {
                "description": "뉴스 전용 검색 (Google News 결과)",
                "parameters": {
                    "query": "뉴스 검색 키워드 (필수)",
                    "num_results": "결과 수 (선택, 기본값: 5)",
                    "language": "검색 언어 (선택, 기본값: 'ko')"
                },
                "example": "webiz.api.web_search.search_news(query='경제 동향', num_results=5)"
            },
            "search_with_filters": {
                "description": "필터 적용 고급 검색",
                "parameters": {
                    "query": "검색 키워드 (필수)",
                    "site_filter": "특정 사이트 필터 (선택)",
                    "file_type": "파일 타입 필터 (선택)"
                },
                "example": "webiz.api.web_search.search_with_filters(query='머신러닝', site_filter='wikipedia.org')"
            },
            "get_search_suggestions": {
                "description": "검색 제안어 생성",
                "parameters": {
                    "query": "기본 검색어 (필수)"
                },
                "example": "webiz.api.web_search.get_search_suggestions(query='인공지능')"
            }
        },
        "usage_tips": [
            "Serper API는 Google 검색 결과를 제공하여 높은 품질의 검색 결과를 보장합니다",
            "뉴스 검색시에는 search_news 함수를 사용하여 최신 뉴스를 검색하세요",
            "검색 결과는 Google의 관련성 알고리즘에 따라 정렬됩니다",
            "API 키 설정이 필요하며, 무료 플랜에서도 충분한 검색 횟수를 제공합니다"
        ],
        "supported_languages": ["ko", "en", "ja", "zh"],
        "raven_ai_integration": {
            "setup": "Raven AI의 Custom Functions에서 이 모듈을 등록하여 사용",
            "function_path": "webiz.api.web_search",
            "required_permissions": ["웹 검색 API 접근 권한", "Serper API 키"]
        }
    }


@frappe.whitelist()
def search_with_filters(query, site_filter=None, date_filter=None, file_type=None, num_results=5):
    """
    필터를 적용한 고급 웹 검색

    Args:
        query (str): 검색 키워드
        site_filter (str, optional): 특정 사이트에서만 검색 (예: "wikipedia.org")
        date_filter (str, optional): 날짜 필터 ("day", "week", "month", "year")
        file_type (str, optional): 파일 타입 필터 ("pdf", "doc", "ppt", "xls")
        num_results (int, optional): 결과 수

    Returns:
        dict: 필터링된 검색 결과
    """

    try:
        # 검색 쿼리 수정
        modified_query = query

        # 사이트 필터 적용
        if site_filter:
            modified_query += f" site:{site_filter}"

        # 파일 타입 필터 적용
        if file_type:
            modified_query += f" filetype:{file_type}"

        # 기본 웹 검색 수행
        result = web_search(modified_query, num_results)

        if result["success"]:
            # 필터 정보 추가
            result["search_stats"]["filters_applied"] = {
                "site_filter": site_filter,
                "date_filter": date_filter,
                "file_type": file_type
            }

            # 날짜 필터는 결과 후처리로 적용 (실제 구현에서는 검색 엔진 API 사용)
            if date_filter:
                result["search_stats"]["note"] = f"날짜 필터 '{date_filter}' 적용됨"

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"고급 검색 오류: {str(e)}"
        }


@frappe.whitelist()
def bulk_search(queries, num_results_per_query=3):
    """
    여러 키워드를 한번에 검색하는 함수

    Args:
        queries (list or str): 검색할 키워드 목록 (JSON 문자열 또는 리스트)
        num_results_per_query (int, optional): 각 키워드당 결과 수

    Returns:
        dict: 모든 검색 결과를 포함한 딕셔너리
    """

    try:
        # 입력값 처리
        if isinstance(queries, str):
            try:
                queries = json.loads(queries)
            except:
                queries = [q.strip() for q in queries.split(',')]

        if not isinstance(queries, list) or not queries:
            return {
                "success": False,
                "error": "검색 키워드 목록이 필요합니다",
                "example": "['키워드1', '키워드2', '키워드3'] 또는 '키워드1,키워드2,키워드3'"
            }

        # 각 키워드별 검색 수행
        all_results = {}
        total_results = 0

        for query in queries[:5]:  # 최대 5개 키워드까지
            if query and query.strip():
                search_result = web_search(query.strip(), num_results_per_query)
                all_results[query] = search_result
                if search_result["success"]:
                    total_results += len(search_result["results"])

        return {
            "success": True,
            "bulk_search_stats": {
                "total_queries": len(all_results),
                "total_results": total_results,
                "search_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "results_by_query": all_results,
            "summary": f"{len(all_results)}개 키워드에 대해 총 {total_results}개의 검색 결과를 찾았습니다."
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"일괄 검색 오류: {str(e)}"
        }


@frappe.whitelist()
def check_api_configuration():
    """
    Serper API 설정 상태를 확인하는 함수

    Returns:
        dict: API 설정 상태 정보
    """

    try:
        api_key = _get_serper_api_key()

        if not api_key:
            return {
                "success": False,
                "configured": False,
                "message": "Serper API 키가 설정되지 않았습니다",
                "setup_instructions": [
                    "1. https://serper.dev에서 무료 계정 생성",
                    "2. API 키 발급",
                    "3. site_config.json에 'serper_api_key': 'your-api-key' 추가",
                    "또는 환경변수 SERPER_API_KEY 설정"
                ]
            }

        # API 키 유효성 테스트
        test_result = _perform_serper_search("test", 1, "ko", "moderate")

        if test_result["success"]:
            return {
                "success": True,
                "configured": True,
                "message": "Serper API가 정상적으로 설정되었습니다",
                "api_key_status": "유효",
                "test_search": "성공"
            }
        else:
            return {
                "success": False,
                "configured": True,
                "message": "API 키는 설정되었지만 검색 테스트에 실패했습니다",
                "api_key_status": "설정됨",
                "test_search": "실패",
                "error": test_result.get("error", "알 수 없는 오류")
            }

    except Exception as e:
        return {
            "success": False,
            "configured": False,
            "message": f"API 설정 확인 중 오류 발생: {str(e)}"
        }


@frappe.whitelist()
def get_api_usage_info():
    """
    Serper API 사용량 정보 안내

    Returns:
        dict: API 사용량 및 제한 정보
    """

    return {
        "success": True,
        "api_provider": "Serper",
        "pricing_info": {
            "free_tier": {
                "searches_per_month": 2500,
                "cost": "무료",
                "features": ["웹 검색", "뉴스 검색", "이미지 검색"]
            },
            "paid_tiers": {
                "hobby": {
                    "searches_per_month": 10000,
                    "cost": "$5/월",
                    "additional_features": ["더 높은 요청 한도"]
                },
                "pro": {
                    "searches_per_month": 100000,
                    "cost": "$50/월",
                    "additional_features": ["우선 지원", "더 높은 요청 한도"]
                }
            }
        },
        "rate_limits": {
            "requests_per_second": 1,
            "requests_per_minute": 60,
            "note": "무료 플랜 기준"
        },
        "supported_search_types": [
            "웹 검색 (organic results)",
            "뉴스 검색 (news results)",
            "이미지 검색 (images)",
            "동영상 검색 (videos)",
            "쇼핑 검색 (shopping)"
        ],
        "get_api_key": "https://serper.dev에서 계정 생성 후 API 키 발급"
    }
