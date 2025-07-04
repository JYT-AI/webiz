import frappe
from datetime import datetime
import pytz
from frappe import _


@frappe.whitelist()
def current_datetime(country=None, timezone=None):
    """
    특정 국가나 시간대의 현재 시간을 반환하는 함수
    AI Agent에서 tool로 호출할 수 있도록 설계됨
    
    Args:
        country (str, optional): 국가명 (예: "Korea", "Japan", "USA", "UK", "Germany")
        timezone (str, optional): 시간대 (예: "Asia/Seoul", "America/New_York")
    
    Returns:
        dict: 현재 시간 정보를 포함한 딕셔너리
    """
    
    # 국가별 기본 시간대 매핑
    country_timezone_map = {
        "korea": "Asia/Seoul",
        "south korea": "Asia/Seoul", 
        "한국": "Asia/Seoul",
        "대한민국": "Asia/Seoul",
        "japan": "Asia/Tokyo",
        "일본": "Asia/Tokyo",
        "china": "Asia/Shanghai",
        "중국": "Asia/Shanghai",
        "usa": "America/New_York",
        "united states": "America/New_York",
        "미국": "America/New_York",
        "uk": "Europe/London",
        "united kingdom": "Europe/London",
        "england": "Europe/London",
        "영국": "Europe/London",
        "germany": "Europe/Berlin",
        "독일": "Europe/Berlin",
        "france": "Europe/Paris",
        "프랑스": "Europe/Paris",
        "australia": "Australia/Sydney",
        "호주": "Australia/Sydney",
        "singapore": "Asia/Singapore",
        "싱가포르": "Asia/Singapore",
        "thailand": "Asia/Bangkok",
        "태국": "Asia/Bangkok",
        "vietnam": "Asia/Ho_Chi_Minh",
        "베트남": "Asia/Ho_Chi_Minh",
        "india": "Asia/Kolkata",
        "인도": "Asia/Kolkata",
        "russia": "Europe/Moscow",
        "러시아": "Europe/Moscow",
        "canada": "America/Toronto",
        "캐나다": "America/Toronto",
        "brazil": "America/Sao_Paulo",
        "브라질": "America/Sao_Paulo",
        "mexico": "America/Mexico_City",
        "멕시코": "America/Mexico_City"
    }
    
    try:
        # 시간대 결정
        target_timezone = None
        
        if timezone:
            # 직접 시간대가 제공된 경우
            target_timezone = timezone
        elif country:
            # 국가명으로 시간대 찾기
            country_lower = country.lower().strip()
            target_timezone = country_timezone_map.get(country_lower)
            
            if not target_timezone:
                # 국가명을 찾을 수 없는 경우 사용 가능한 국가 목록 반환
                available_countries = list(set([k for k in country_timezone_map.keys() if not k.startswith(('asia/', 'america/', 'europe/', 'australia/'))]))
                return {
                    "success": False,
                    "error": f"지원하지 않는 국가입니다: {country}",
                    "available_countries": sorted(available_countries),
                    "message": "위 국가명 중 하나를 사용하거나 정확한 시간대를 입력해주세요 (예: Asia/Seoul)"
                }
        else:
            # 기본값: 한국 시간
            target_timezone = "Asia/Seoul"
        
        # 시간대 객체 생성
        tz = pytz.timezone(target_timezone)
        
        # 현재 시간 계산
        utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        local_time = utc_now.astimezone(tz)
        
        # 시간대 정보
        timezone_info = {
            "timezone": target_timezone,
            "timezone_name": tz.zone,
            "utc_offset": local_time.strftime('%z'),
            "dst_active": bool(local_time.dst())
        }
        
        # 결과 반환
        result = {
            "success": True,
            "current_datetime": local_time.strftime('%Y-%m-%d %H:%M:%S'),
            "current_date": local_time.strftime('%Y-%m-%d'),
            "current_time": local_time.strftime('%H:%M:%S'),
            "day_of_week": local_time.strftime('%A'),
            "timezone_info": timezone_info,
            "utc_datetime": utc_now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            "formatted_display": f"{local_time.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')} ({target_timezone})"
        }
        
        # 요청된 국가 정보 추가
        if country:
            result["requested_country"] = country
            
        return result
        
    except pytz.exceptions.UnknownTimeZoneError:
        return {
            "success": False,
            "error": f"알 수 없는 시간대입니다: {target_timezone}",
            "message": "올바른 시간대 형식을 사용해주세요 (예: Asia/Seoul, America/New_York)"
        }
    except Exception as e:
        frappe.log_error(f"current_datetime API 오류: {str(e)}")
        return {
            "success": False,
            "error": "시간 정보를 가져오는 중 오류가 발생했습니다",
            "message": str(e)
        }


@frappe.whitelist()
def get_supported_countries():
    """
    지원하는 국가 목록을 반환하는 함수
    
    Returns:
        dict: 지원하는 국가와 시간대 정보
    """
    
    country_timezone_map = {
        "Korea": "Asia/Seoul",
        "Japan": "Asia/Tokyo", 
        "China": "Asia/Shanghai",
        "USA": "America/New_York",
        "UK": "Europe/London",
        "Germany": "Europe/Berlin",
        "France": "Europe/Paris",
        "Australia": "Australia/Sydney",
        "Singapore": "Asia/Singapore",
        "Thailand": "Asia/Bangkok",
        "Vietnam": "Asia/Ho_Chi_Minh",
        "India": "Asia/Kolkata",
        "Russia": "Europe/Moscow",
        "Canada": "America/Toronto",
        "Brazil": "America/Sao_Paulo",
        "Mexico": "America/Mexico_City"
    }
    
    return {
        "success": True,
        "supported_countries": country_timezone_map,
        "total_countries": len(country_timezone_map),
        "usage_example": "webiz.api.current_datetime(country='Korea') 또는 webiz.api.current_datetime(timezone='Asia/Seoul')"
    }


@frappe.whitelist()
def get_timezone_list():
    """
    사용 가능한 모든 시간대 목록을 반환하는 함수
    
    Returns:
        dict: 시간대 목록
    """
    
    # 주요 시간대만 선별하여 반환
    major_timezones = [
        "Asia/Seoul", "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore",
        "Asia/Bangkok", "Asia/Ho_Chi_Minh", "Asia/Kolkata", "Asia/Dubai",
        "Europe/London", "Europe/Berlin", "Europe/Paris", "Europe/Rome",
        "Europe/Moscow", "America/New_York", "America/Chicago", 
        "America/Denver", "America/Los_Angeles", "America/Toronto",
        "America/Sao_Paulo", "America/Mexico_City", "Australia/Sydney",
        "Australia/Melbourne", "Pacific/Auckland"
    ]
    
    return {
        "success": True,
        "major_timezones": major_timezones,
        "total_timezones": len(major_timezones),
        "note": "주요 시간대만 표시됩니다. 다른 시간대가 필요한 경우 정확한 시간대명을 입력해주세요."
    }
