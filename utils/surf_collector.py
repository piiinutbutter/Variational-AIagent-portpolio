"""
SurfAI 소셜 분석 데이터 수집 유틸리티
크립토 소셜 영향력, KOL 토론, 시장 심리 데이터 수집

API: https://api.asksurf.ai/surf-ai
Docs: https://docs.asksurf.ai
"""
import requests
from datetime import datetime
from config.settings import SURF_API_KEY
from utils.logger import get_logger

log = get_logger("SurfAI")

BASE_URL = "https://api.asksurf.ai/surf-ai/v1"


def _get_headers() -> dict:
    """인증 헤더 생성"""
    return {"Authorization": f"Bearer {SURF_API_KEY}"}


def _is_available() -> bool:
    """SurfAI API 사용 가능 여부"""
    return bool(SURF_API_KEY)


def _api_get(endpoint: str, params: dict = None) -> dict | None:
    """SurfAI API GET 요청"""
    if not _is_available():
        return None

    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data")
            else:
                log.warning(f"API 응답 실패: {data.get('message', 'unknown')}")
                return None
        elif response.status_code == 401:
            log.error("SurfAI API 인증 실패 — API 키 확인 필요")
            return None
        elif response.status_code == 429:
            log.warning("SurfAI rate limit 초과")
            return None
        else:
            log.error(f"SurfAI API 오류: {response.status_code}")
            return None
    except requests.RequestException as e:
        log.error(f"SurfAI 네트워크 오류: {e}")
        return None


def get_market_sentiment() -> str:
    """시장 심리 (Fear/Greed 지수)"""
    data = _api_get("/market/sentiment")
    if not data:
        return ""

    fgi = data.get("feer_greed_index", "N/A")
    interpretation = data.get("feer_greed_interpretation", "N/A")
    fluctuations = data.get("market_price_fluctuations", [])
    rising = data.get("rising_assets_vs_previous_day", "N/A")

    output = "[SurfAI 시장 심리]\n"
    output += f"- Fear & Greed Index: {fgi} ({interpretation})\n"
    output += f"- 전일 대비 상승 자산 수: {rising}\n"

    for f in fluctuations:
        label = {"UP": "상승", "FLAT": "보합", "DOWN": "하락"}.get(f.get("type", ""), f.get("type", ""))
        output += f"- {label}: {f.get('num', 0)}개\n"

    return output


def get_kol_discussions() -> str:
    """KOL 토론/인기 트윗 동향"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = _api_get("/market/ai-recommended-prompts", {"type": "kols_discuss", "date": today})
    if not data:
        return ""

    content = data.get("content", "")
    if not content:
        return ""

    return f"[SurfAI KOL 토론 동향]\n{content}"


def get_kol_sectors() -> str:
    """KOL 섹터별 관심 분석"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = _api_get("/market/ai-recommended-prompts", {"type": "kols_sectors", "date": today})
    if not data:
        return ""

    content = data.get("content", "")
    if not content:
        return ""

    return f"[SurfAI KOL 섹터 분석]\n{content}"


def get_social_report(ticker: str = "BTC") -> str:
    """소셜 데이터 분석 리포트"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = _api_get("/market/ai-report", {"type": "social_data", "ticker": ticker, "date": today})
    if not data:
        return ""

    content = data.get("content", "")
    if not content:
        return ""

    return f"[SurfAI 소셜 분석 - {ticker}]\n{content}"


def get_trending_issues() -> str:
    """트렌딩 이슈"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = _api_get("/market/ai-recommended-prompts", {"type": "trending_issues", "date": today})
    if not data:
        return ""

    content = data.get("content", "")
    if not content:
        return ""

    return f"[SurfAI 트렌딩 이슈]\n{content}"


def collect_all_surf_data() -> str:
    """SurfAI 소셜 데이터 전체 수집"""
    if not _is_available():
        log.info("SURF_API_KEY 미설정 — SurfAI 수집 스킵")
        return ""

    log.info("SurfAI 소셜 데이터 수집 시작...")
    parts = []

    # 1. 시장 심리
    sentiment = get_market_sentiment()
    if sentiment:
        parts.append(sentiment)

    # 2. KOL 토론 (인기 트윗/소셜 영향력)
    kol = get_kol_discussions()
    if kol:
        parts.append(kol)

    # 3. KOL 섹터 분석
    sectors = get_kol_sectors()
    if sectors:
        parts.append(sectors)

    # 4. BTC 소셜 리포트
    social = get_social_report("BTC")
    if social:
        parts.append(social)

    # 5. ETH 소셜 리포트
    social_eth = get_social_report("ETH")
    if social_eth:
        parts.append(social_eth)

    # 6. 트렌딩 이슈
    trending = get_trending_issues()
    if trending:
        parts.append(trending)

    if parts:
        log.info(f"SurfAI 데이터 수집 완료 ({len(parts)}개 항목)")
        return "\n\n".join(parts)
    else:
        log.warning("SurfAI 데이터 수집 결과 없음")
        return ""


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    result = collect_all_surf_data()
    if result:
        print(result)
    else:
        print("SurfAI 수집 불가 — API 키 확인 필요")
