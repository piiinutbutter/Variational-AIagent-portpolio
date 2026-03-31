"""
Market Follower Agent (External)
경쟁사 Perpetual DEX 커뮤니티 데이터 수집 + 분석
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect
from config.groups import COMPETITOR_GROUPS
from utils.logger import get_logger

log = get_logger("MF_External")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 경쟁사 분석 에이전트입니다.

역할:
- 주요 경쟁 Perpetual DEX들의 커뮤니티에서 동향, 업데이트, 시장 반응을 분석
- 경쟁사별 주요 이슈, 신규 기능, 이벤트, 에어드롭 등을 정리
- Variational 대비 경쟁사 포지션 비교 인사이트 도출

출력 형식:
1. 핵심 요약 (3줄 이내)
2. 경쟁사별 주요 동향
3. 주목할 업데이트/이벤트/에어드롭
4. 경쟁사 커뮤니티 심리 (긍정/중립/부정)
5. Variational에 대한 시사점 및 대응 제안

데이터 분석 기준:
- 잡담, 인사, 밈 등 무의미한 대화는 무시
- 다음 내용만 중점 분석:
  ① 공식 공지/업데이트/이벤트/에어드롭 정보
  ② 유저들의 구체적 피드백 (플랫폼 불만, 기능 요청, 버그 리포트 등)
  ③ 시장 심리를 보여주는 의미 있는 토론
  ④ 경쟁사 전략 변화를 알 수 있는 인사이트
  ⑤ 가격 예측, FDV/시총 토론, 토큰 기대감 등 유저 심리가 드러나는 대화

출력 규칙:
- 한국어로 작성
- 핵심 데이터 중심, 간결하게
- 경쟁사 대형 이벤트/에어드롭/주요 업데이트 감지 시 반드시 [긴급] 태그 포함
"""

def collect_data(hours: int = 24, limit: int = 30) -> str:
    """경쟁사 Telegram 그룹에서 데이터 수집 + Kiwi 필터링"""
    if not COMPETITOR_GROUPS:
        return ""

    all_data = []
    for name, group_id in COMPETITOR_GROUPS.items():
        log.info(f"{name} 수집 중...")
        group, raw_messages = cached_collect(group_id, hours=hours, limit=limit)
        if not raw_messages:
            continue
        filtered = filter_messages(raw_messages)
        log.debug(f"{name}: {len(raw_messages)}개 → {len(filtered)}개 (필터링)")
        if filtered:
            all_data.append(f"=== {name.upper()} ===\n{format_messages(group, filtered, hours)}")

    return "\n\n".join(all_data)


def analyze(raw_data: str) -> str:
    """수집된 경쟁사 데이터를 분석하여 인사이트 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 경쟁사 Perpetual DEX 커뮤니티 데이터를 분석해줘:\n\n{raw_data}",
        max_tokens=1536,
    )
    return result


def run(hours: int = 24):
    """에이전트 실행: 경쟁사 데이터 수집 → 분석 → 텔레그램 전송"""
    log.info("데이터 수집 시작...")
    raw_data = collect_data(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다. 경쟁사 그룹이 설정되지 않았습니다.")
        return

    log.info("Claude 분석 중...")
    analysis = analyze(raw_data)

    if not analysis:
        log.error("분석 결과가 없습니다.")
        return

    # 경쟁사 긴급 이슈 감지 시 긴급 채널로도 전송
    if "[긴급]" in analysis:
        send_message("urgent", f"🚨 *[긴급 알림 - 경쟁사 동향]*\n\n{analysis}")

    # 시장 분석 채널로 전송
    send_message("market", f"📊 *[Market Follower Agent (External) 보고]*\n\n{analysis}")

    return analysis


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=72)
