"""
Promotion Agent
한국 시장 대상 마케팅 전략 수립 + 캠페인 기획
각 에이전트 데이터를 참고하여 마케팅 기획안 작성
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.data_cache import cached_competitor_data
from agents.trend_research_agent import collect_trends
from utils.logger import get_logger

log = get_logger("Promotion")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 한국 시장 마케팅 기획 에이전트입니다.

역할:
- 경쟁사 동향 + 트렌드 데이터를 기반으로 마케팅 전략 수립
- 한국 시장 대상 캠페인/이벤트/프로모션 기획
- KOL 협업 제안서 초안 작성
- 채널별 최적 전략 설계

출력 형식:
1. 시장 상황 요약 (경쟁사 + 트렌드 기반)

2. 마케팅 기획안 (2~3개)
   각 기획안마다:
   - 캠페인명
   - 목적 (신규 유저 유입 / 거래량 부스트 / 브랜드 인지도 등)
   - 타겟 오디언스
   - 실행 방법 (구체적 스텝)
   - 예상 비용 범위
   - 기대 효과 (KPI)
   - 실행 타이밍

3. KOL 협업 제안 (해당 시)
   - 추천 KOL 유형
   - 협업 형태 (리뷰, AMA, 공동 이벤트 등)
   - 예상 비용

4. 채널별 전략
   - X, Telegram, Discord 각 채널 최적 전략

마케팅 원칙:
- Variational의 강점 (Perpetual DEX, 속도, 유동성) 활용
- 경쟁사와 차별화되는 포인트 강조
- 한국 크립토 커뮤니티 문화에 맞는 접근
- 실행 가능하고 비용 효율적인 기획
- 한국어로 작성
"""


def collect_market_data(hours: int = 72) -> str:
    """경쟁사 + 트렌드 데이터 수집"""
    parts = []

    log.info("경쟁사 데이터 수집 중...")
    competitor_data = cached_competitor_data(hours=hours)
    if competitor_data:
        parts.append(f"=== 경쟁사 동향 ===\n{competitor_data}")

    log.info("트렌드 데이터 수집 중...")
    trend_data = collect_trends(hours=hours)
    if trend_data:
        parts.append(f"=== 시장 트렌드 ===\n{trend_data}")

    return "\n\n".join(parts)


def create_plan(market_data: str) -> str:
    """마케팅 기획안 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 시장 데이터를 기반으로 Variational 한국 시장 마케팅 기획안을 작성해줘:\n\n{market_data}",
        max_tokens=3072,
    )
    return result


def run(hours: int = 72):
    """에이전트 실행: 데이터 수집 → 마케팅 기획 → 텔레그램 전송"""
    log.info("마케팅 기획 시작...")
    market_data = collect_market_data(hours=hours)

    if not market_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 마케팅 기획 중...")
    plan = create_plan(market_data)

    if not plan:
        log.error("기획안 생성 실패.")
        return

    # Q&A+마케팅 채널로 전송
    send_message("qa_marketing", f"📢 *[Promotion Agent - 마케팅 기획안]*\n\n{plan}")

    log.info("마케팅 기획안 전송 완료.")
    return plan


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=72)
