"""
Trend Research Agent
크립토 트렌드/밈 모니터링 + 콘텐츠 소재 발굴
Market Follower Agent (External) 경쟁사 동태 참고
"""
from utils.llm import ask_claude
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect, cached_market_data, cached_x_data, cached_surf_data, cached_mindshare, save_agent_result
from config.groups import get_trend_groups
from utils.logger import get_logger

log = get_logger("TrendResearch")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 트렌드 리서치 에이전트입니다.

역할:
- 한국 크립토 커뮤니티에서 자주 언급되는 트렌드, 밈, 화제를 포착
- 조회수/댓글이 많은 핫한 주제를 발굴
- Variational 콘텐츠로 활용할 수 있는 소재를 리서치
- 경쟁사 동태를 참고하여 트렌드와 연결

출력 형식:
1. 이번 주 핵심 트렌드 (3~5개)
   - 트렌드명, 왜 화제인지, 관련 키워드
2. 밈/바이럴 콘텐츠
   - 현재 유행 중인 밈이나 바이럴 요소
3. Variational 콘텐츠 소재 추천
   - 각 트렌드를 Variational 콘텐츠로 어떻게 활용할 수 있는지 구체적 아이디어
4. 경쟁사 콘텐츠 동향
   - 경쟁사가 어떤 콘텐츠/이벤트로 주목받고 있는지
5. X(Twitter) 트렌드
   - X에서 화제인 Perpetual DEX 관련 트윗/토론
   - 경쟁사 X 계정의 주요 활동 (좋아요/RT 높은 게시물)
6. 소셜 영향력 분석 (SurfAI)
   - KOL들이 주목하는 토론/섹터
   - 트렌딩 이슈와 Variational 활용 가능성

출력 규칙:
- 한국어로 작성
- 각 트렌드에 활용 가능성 점수 (★~★★★★★) 포함
- 시의성이 중요한 트렌드는 [시급] 태그 포함
"""

def collect_trends(hours: int = 72, limit: int = 30) -> str:
    """트렌드 소스에서 데이터 수집 + 필터링"""
    all_data = []
    for group_name in get_trend_groups():
        group, raw_messages = cached_collect(group_name, hours=hours, limit=limit)
        if not raw_messages:
            continue
        filtered = filter_messages(raw_messages)
        log.debug(f"{group}: {len(raw_messages)}개 → {len(filtered)}개")
        if filtered:
            all_data.append(format_messages(group, filtered, hours))
    return "\n\n".join(all_data)


def analyze_trends(raw_data: str, hours: int = 72) -> str:
    """트렌드 데이터 분석 + 콘텐츠 소재 발굴 (시장 데이터 포함)"""
    # 실시간 시장 데이터 추가
    log.info("실시간 시장 데이터(DeFiLlama/CoinGecko) 수집 중...")
    market_data = cached_market_data()

    # X(Twitter) 데이터 추가
    log.info("X(Twitter) 데이터 수집 중...")
    x_data = cached_x_data()

    combined = raw_data
    if market_data:
        combined = f"=== 실시간 시장 데이터 ===\n{market_data}\n\n=== 커뮤니티 데이터 ===\n{raw_data}"
    if x_data:
        combined += f"\n\n=== X(Twitter) 데이터 ===\n{x_data}"

    # SurfAI 소셜 영향력 데이터 추가
    log.info("SurfAI 소셜 분석 데이터 수집 중...")
    surf_data = cached_surf_data()
    if surf_data:
        combined += f"\n\n=== SurfAI 소셜 영향력 분석 ===\n{surf_data}"

    # 한국 커뮤니티 Mindshare 데이터 추가
    log.info("한국 커뮤니티 Mindshare 산출 중...")
    mindshare_data = cached_mindshare(hours=hours)
    if mindshare_data:
        combined += f"\n\n=== 한국 커뮤니티 Mindshare ===\n{mindshare_data}"

    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 시장 데이터와 한국 크립토 커뮤니티 데이터를 종합하여 트렌드를 분석하고 Variational 콘텐츠 소재를 발굴해줘:\n\n{combined}",
    )
    return result


def run(hours: int = 72):
    """에이전트 실행: 트렌드 수집 → 분석 → 결과 반환 (Contents Creator Agent에게 전달)"""
    log.info("트렌드 수집 시작...")
    raw_data = collect_trends(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 트렌드 분석 중...")
    trends = analyze_trends(raw_data, hours=hours)

    if not trends:
        log.error("트렌드 분석 실패.")
        return

    # POC Agent가 재사용할 수 있도록 결과 캐시 저장
    save_agent_result("trend_research", trends)

    log.info("트렌드 분석 완료 → Contents Creator Agent에게 전달.")
    return trends


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    result = run(hours=72)
    if result:
        print(result)
