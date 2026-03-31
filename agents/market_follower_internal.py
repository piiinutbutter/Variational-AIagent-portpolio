"""
Market Follower Agent (Internal)
Variational 커뮤니티 데이터 수집 + 분석
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from utils.telegram_collector import format_messages
from utils.message_filter import filter_messages
from utils.data_cache import cached_collect
from config.groups import VARIATIONAL_GROUPS
from utils.logger import get_logger

log = get_logger("MF_Internal")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 한국 시장 데이터 수집 에이전트입니다.

역할:
- Telegram 커뮤니티에서 한국 이용자들의 Variational에 대한 반응과 시장 심리를 분석
- 주요 토론 주제, 사용자 피드백, 질문을 정리
- KPI 데이터 (메시지 수, 참여도 등) 정리

출력 형식:
1. 핵심 요약 (3줄 이내)
2. 주요 토론 주제
3. 사용자 피드백/질문 정리
4. 시장 심리 판단 (긍정/중립/부정)
5. 특이사항 또는 주의 필요 사항

데이터 분석 기준:
- 잡담, 인사, 밈 등 무의미한 대화는 무시
- 다음 내용만 중점 분석:
  ① 유저들의 구체적 피드백 (플랫폼 불만, 기능 요청, 버그 리포트 등)
  ② Variational에 대한 의미 있는 질문
  ③ 시장 심리를 보여주는 구체적 토론
  ④ 공식 공지에 대한 유저 반응
  ⑤ 가격 예측, FDV/시총 토론, 토큰 기대감 등 유저 심리가 드러나는 대화

출력 규칙:
- 한국어로 작성
- 핵심 데이터 중심, 간결하게
- 긴급 이슈(FUD 확산, 플랫폼 장애 불만 폭주 등)가 있으면 반드시 [긴급] 태그 포함
"""

def collect_data(hours: int = 24, limit: int = 30) -> str:
    """Telegram 그룹에서 데이터 수집 + Kiwi 필터링"""
    all_data = []
    for group_name in VARIATIONAL_GROUPS:
        group, raw_messages = cached_collect(group_name, hours=hours, limit=limit)
        if not raw_messages:
            continue
        filtered = filter_messages(raw_messages)
        log.debug(f"{group}: {len(raw_messages)}개 → {len(filtered)}개 (필터링)")
        if filtered:
            all_data.append(format_messages(group, filtered, hours))
    return "\n\n".join(all_data)


def analyze(raw_data: str) -> str:
    """수집된 원시 데이터를 분석하여 인사이트 생성"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 데이터를 분석하고 핵심 인사이트를 정리해줘:\n\n{raw_data}",
        max_tokens=1536,
    )
    return result


def run(hours: int = 24):
    """에이전트 실행: 데이터 수집 → 분석 → 텔레그램 전송"""
    log.info("데이터 수집 시작...")
    raw_data = collect_data(hours=hours)

    if not raw_data:
        log.error("수집된 데이터가 없습니다.")
        return

    log.info("Claude 분석 중...")
    analysis = analyze(raw_data)

    if not analysis:
        log.error("분석 결과가 없습니다.")
        return

    # 긴급 이슈 감지 시 긴급 채널로도 전송
    if "[긴급]" in analysis:
        send_message("urgent", f"🚨 *[긴급 알림 - Variational]*\n\n{analysis}")

    # 시장 분석 채널로 전송
    send_message("market", f"📊 *[Market Follower Agent (Internal) 보고]*\n\n{analysis}")

    return analysis


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=168)
