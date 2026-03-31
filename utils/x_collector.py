"""
X (Twitter) 데이터 수집 유틸리티

현재 상태:
- Apify 무료 플랜으로는 X 검색 기능이 제한됨
- 유료 API 전환 시 즉시 활성화 가능하도록 구조만 준비
- 채용 후 X API (Basic $100/월) 또는 Apify 유료 플랜으로 전환 예정

지원 Actor (유료 전환 시):
- apidojo/tweet-scraper (1.35억 runs, 가장 안정적)
- apidojo/twitter-scraper-lite (1,100만 runs)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from apify_client import ApifyClient
from config.settings import APIFY_API_TOKEN, X_BEARER_TOKEN
from utils.logger import get_logger

log = get_logger("X_Collector")

# 유료 전환 시 사용할 Actor
PAID_ACTOR_ID = "apidojo/tweet-scraper"

# 무료 플랜 감지 플래그 (한 번 감지되면 파이프라인 동안 재시도 안 함)
_free_plan_detected = False

# Variational + 경쟁사 X 계정
MONITORED_ACCOUNTS = {
    "Variational": "variaboratory",
    "Hyperliquid": "HyperliquidX",
    "edgeX": "edgeX_exchange",
    "GRVT": "grvt_official",
    "Lighter": "lighter_xyz",
    "BasedApp": "BasedOneX",
}

# 트렌드 검색 키워드
TREND_KEYWORDS = [
    "Variational DEX",
    "Perpetual DEX",
    "basedapp",
    "based DEX",
    "베이스드",
]


def _is_available() -> bool:
    """X 수집 기능 사용 가능 여부 확인"""
    # X API (Bearer Token)가 있으면 공식 API 사용
    if X_BEARER_TOKEN:
        return True
    # Apify 유료 플랜 확인은 실행 시 판단
    if APIFY_API_TOKEN:
        return True
    return False


def _get_apify_client() -> ApifyClient | None:
    """Apify 클라이언트 반환"""
    if not APIFY_API_TOKEN:
        return None
    return ApifyClient(APIFY_API_TOKEN)


def _parse_tweet(item: dict) -> dict:
    """Apify 결과를 통일된 형식으로 변환"""
    author = item.get("author", {})
    return {
        "author": author.get("userName", item.get("user_name", "unknown")),
        "text": item.get("text", item.get("full_text", "")),
        "likes": item.get("likeCount", item.get("favorite_count", 0)) or 0,
        "retweets": item.get("retweetCount", item.get("retweet_count", 0)) or 0,
        "replies": item.get("replyCount", item.get("reply_count", 0)) or 0,
        "quotes": item.get("quoteCount", item.get("quote_count", 0)) or 0,
        "views": item.get("viewCount", item.get("views_count", 0)) or 0,
        "date": item.get("createdAt", item.get("created_at", "")),
    }


def search_tweets(keyword: str, max_tweets: int = 10) -> str:
    """키워드로 트윗 검색 (유료 플랜 필요)"""
    global _free_plan_detected

    # 이미 무료 플랜으로 감지되었으면 Apify 호출 스킵
    if _free_plan_detected:
        return ""

    client = _get_apify_client()
    if not client:
        return ""

    run_input = {
        "searchTerms": [keyword],
        "maxTweets": max_tweets,
        "sort": "Latest",
    }

    log.info(f"'{keyword}' 키워드 검색 중...")

    try:
        run = client.actor(PAID_ACTOR_ID).call(run_input=run_input)

        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # 유료 플랜 미사용 시 noResults 키 반환
            if "noResults" in item:
                _free_plan_detected = True
                log.warning("유료 플랜 필요 — 이후 X 수집 전체 스킵")
                return ""
            tweet = _parse_tweet(item)
            if tweet["text"]:
                results.append(tweet)

        if results:
            log.info(f"'{keyword}' — {len(results)}개 트윗 수집 완료")
            return _format_tweets(f"키워드: {keyword}", results)
        else:
            log.info(f"'{keyword}' 검색 결과 없음")
            return ""

    except Exception as e:
        log.error(f"X 수집 실패 ({keyword}): {e}")
        return ""


def get_user_tweets(username: str, max_tweets: int = 5) -> str:
    """특정 계정의 최근 트윗 수집 (유료 플랜 필요)"""
    return search_tweets(f"from:{username}", max_tweets)


def collect_competitor_tweets(max_per_account: int = 5) -> str:
    """경쟁사 X 계정 트윗 일괄 수집"""
    parts = []

    for name, handle in MONITORED_ACCOUNTS.items():
        result = get_user_tweets(handle, max_tweets=max_per_account)
        if result:
            parts.append(f"=== {name} (@{handle}) ===\n{result}")
        else:
            # 첫 번째 실패 시 유료 플랜 미사용으로 판단하고 중단
            if not parts:
                log.warning("유료 플랜 미활성 — 경쟁사 수집 중단")
                return ""

    if parts:
        return "[X (Twitter) 경쟁사 트윗 수집]\n\n" + "\n\n".join(parts)
    return ""


def collect_trend_tweets(max_per_keyword: int = 10) -> str:
    """트렌드 키워드 기반 트윗 수집"""
    parts = []

    for keyword in TREND_KEYWORDS:
        result = search_tweets(keyword, max_tweets=max_per_keyword)
        if result:
            parts.append(result)
        else:
            if not parts:
                log.warning("유료 플랜 미활성 — 트렌드 수집 중단")
                return ""

    if parts:
        return "[X (Twitter) 트렌드 수집]\n\n" + "\n\n".join(parts)
    return ""


def collect_all_x_data(max_per_account: int = 5, max_per_keyword: int = 10) -> str:
    """X 데이터 전체 수집 (경쟁사 + 트렌드)"""
    if not _is_available():
        log.info("API 미설정 — X 수집 스킵")
        return ""

    parts = []

    log.info("경쟁사 X 계정 수집 시작...")
    competitor = collect_competitor_tweets(max_per_account)
    if competitor:
        parts.append(competitor)

    # 무료 플랜 감지 시 트렌드 수집도 스킵 (Apify 호출 낭비 방지)
    if not _free_plan_detected:
        log.info("트렌드 키워드 수집 시작...")
        trends = collect_trend_tweets(max_per_keyword)
        if trends:
            parts.append(trends)

    if not parts:
        log.info("X 수집 결과 없음 (유료 플랜 전환 시 활성화)")

    return "\n\n".join(parts)


def _format_tweets(source: str, tweets: list[dict]) -> str:
    """트윗 리스트를 텍스트로 포맷팅"""
    output = f"[X 수집 데이터 - {source}]\n"
    output += f"총 {len(tweets)}개 트윗\n\n"

    for t in tweets:
        output += (
            f"- @{t['author']} ({t['date']}): \"{t['text'][:200]}\" "
            f"(likes: {t['likes']}, RT: {t['retweets']}, "
            f"replies: {t['replies']}, views: {t['views']})\n"
        )

    return output


if __name__ == "__main__":
    result = collect_all_x_data(max_per_account=3, max_per_keyword=5)
    if result:
        print("\n" + result)
    else:
        print("X 수집 불가 — 유료 플랜 전환 필요")
