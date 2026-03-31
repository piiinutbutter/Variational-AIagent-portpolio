"""
Report Agent
Market Follower Agent (Internal + External) 데이터를 종합하여 일간/주간 보고서 작성
"""
from utils.llm import ask_claude
from utils.data_cache import cached_collect, cached_market_data, cached_x_data, cached_competitor_data, cached_surf_data, cached_mindshare
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from config.groups import VARIATIONAL_GROUPS
from utils.logger import get_logger

log = get_logger("Report")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 시장 분석 보고서 작성 에이전트입니다.

역할:
- Market Follower Agent (Internal)과 (External)이 수집한 데이터를 종합 분석
- 일간/주간 보고서를 구조화하여 작성
- Variational의 한국 시장 포지션에 대한 인사이트 도출

보고서 구성:
1. Executive Summary (핵심 3줄 요약)
2. Variational 커뮤니티 동향
   - 주요 토론/피드백/질문
   - 유저 심리 (긍정/중립/부정)
3. 경쟁사 동향 비교
   - 경쟁사별 핵심 움직임
   - Variational 대비 포지션
4. 시장 심리 종합 판단
   - Variational 유저 기대감/우려
   - 경쟁사 대비 강점/약점
5. X(Twitter) 동향
   - Variational/경쟁사 X 계정 활동 분석
   - 주목할 트윗/토론/반응
6. 소셜 영향력 분석 (SurfAI)
   - KOL 토론 동향 및 주목 섹터
   - BTC/ETH 소셜 데이터 트렌드
   - Fear & Greed 지수와 시장 심리
7. 한국 커뮤니티 Mindshare
   - Perp DEX별 한국 커뮤니티 관심도 비교
   - 텔레그램/X/KOL 채널별 상세 점유율
   - Variational의 포지션 및 개선 방향
   ※ 한국 텔레그램·X·KOL 기반 자체 산출 지표 (글로벌 mindshare 아님)
8. 액션 아이템 제안
   - 즉시 대응 필요 사항
   - 중기 전략 제안

데이터 분석 기준:
- 잡담, 인사, 밈 등 무의미한 대화는 무시
- 유저 피드백, 공식 공지, 가격/FDV 토론, 시장 심리 중심으로 분석
- 경쟁사와 Variational을 항상 비교 관점에서 분석

출력 규칙:
- 한국어로 작성
- 데이터 기반, 간결하게
- 긴급 이슈가 있으면 반드시 [긴급] 태그로 시작
"""


def collect_all_data(hours: int = 24) -> str:
    """Internal + External 데이터 동시 수집 (캐시 적용)"""
    log.info("Variational 내부 데이터 수집...")
    internal_parts = []
    for group_name in VARIATIONAL_GROUPS:
        group, raw_messages = cached_collect(group_name, hours=hours)
        if raw_messages:
            filtered = filter_messages(raw_messages)
            if filtered:
                internal_parts.append(format_messages(group, filtered, hours))
    internal = "\n\n".join(internal_parts)

    log.info("경쟁사 데이터 수집...")
    external = cached_competitor_data(hours=hours)

    log.info("실시간 시장 데이터 수집...")
    market_data = cached_market_data()

    log.info("X(Twitter) 데이터 수집...")
    x_data = cached_x_data()

    log.info("SurfAI 소셜 분석 데이터 수집...")
    surf_data = cached_surf_data()

    log.info("한국 커뮤니티 Mindshare 산출...")
    mindshare_data = cached_mindshare(hours=hours)

    parts = []
    if market_data:
        parts.append(f"=== 실시간 시장 데이터 (DeFiLlama/CoinGecko) ===\n{market_data}")
    if internal:
        parts.append(f"=== VARIATIONAL 내부 데이터 ===\n{internal}")
    if external:
        parts.append(f"=== 경쟁사 데이터 ===\n{external}")
    if x_data:
        parts.append(f"=== X(Twitter) 데이터 ===\n{x_data}")
    if surf_data:
        parts.append(f"=== SurfAI 소셜 영향력 분석 ===\n{surf_data}")
    if mindshare_data:
        parts.append(f"=== 한국 커뮤니티 Mindshare ===\n{mindshare_data}")

    return "\n\n".join(parts)


def generate_report(raw_data: str, report_type: str = "일간") -> str:
    """수집된 데이터로 보고서 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 데이터를 기반으로 {report_type} 보고서를 작성해줘:\n\n{raw_data}",
        max_tokens=3072,
    )
    return result


def run(hours: int = 24, report_type: str = "일간"):
    """에이전트 실행: 데이터 수집 → 보고서 초안 생성 (텔레그램 전송 없음, Report Reviewer Agent에게 전달)"""
    log.info(f"{report_type} 보고서 초안 작성 시작...")
    raw_data = collect_all_data(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 보고서 초안 작성 중...")
    report = generate_report(raw_data, report_type)

    if not report:
        log.error("보고서 초안 생성 실패.")
        return

    log.info(f"{report_type} 보고서 초안 완성 → Report Reviewer Agent에게 전달.")
    return report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=72, report_type="일간")
