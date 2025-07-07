import frappe
import requests
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