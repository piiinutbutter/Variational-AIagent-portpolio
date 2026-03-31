"""
Contents Creator Agent
Trend Research Agent의 트렌드 소재 → 콘텐츠 아이디어 + 초안 제작
최종 결과를 콘텐츠 채널로 전송
"""
from utils.llm import ask_claude
from utils.telegram_sender import send_message
from agents.trend_research_agent import run as research_trends
from utils.logger import get_logger

log = get_logger("ContentsCreator")

SYSTEM_PROMPT = """
당신은 Variational (Perpetual DEX)의 한국 시장 콘텐츠 크리에이터 에이전트입니다.

역할:
- Trend Research Agent가 발굴한 트렌드 소재를 기반으로 콘텐츠 기획
- 각 콘텐츠의 아이디어와 초안을 직접 제작
- Variational 브랜드에 맞는 톤앤매너 유지

출력 형식:
1. 콘텐츠 기획안 (3~5개)
   각 기획안마다:
   - 제목/헤드라인
   - 콘텐츠 유형 (트윗, 스레드, 인포그래픽, 밈, 공지 등)
   - 타겟 채널 (X, Telegram, Discord)
   - 핵심 메시지
   - 초안 전문

2. 추천 게시 타이밍
   - 각 콘텐츠별 최적 게시 시간대

3. 기대 효과
   - 예상 반응, 타겟 오디언스

콘텐츠 원칙:
- Variational의 강점 (Perpetual DEX, 한국 시장 특화)을 자연스럽게 녹여내기
- 트렌드에 편승하되 억지스럽지 않게
- 한국 크립토 커뮤니티 문화에 맞는 톤 (너무 딱딱하지 않게)
- 정보성 + 재미 균형
- 유저 참여를 유도하는 CTA(Call to Action) 포함

출력 규칙:
- 한국어로 작성
- 초안은 바로 사용할 수 있을 정도로 완성도 있게
- 시급한 트렌드 콘텐츠는 [시급] 태그 포함
"""


def create_contents(trend_data: str) -> str:
    """트렌드 데이터 기반 콘텐츠 기획 + 초안 제작"""
    result = ask_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=f"아래 트렌드 분석 결과를 기반으로 Variational 콘텐츠를 기획하고 초안을 작성해줘:\n\n{trend_data}",
        max_tokens=3072,
    )
    return result


def run(hours: int = 72):
    """전체 파이프라인: 트렌드 리서치 → 콘텐츠 기획 → 텔레그램 전송"""
    log.info("콘텐츠 파이프라인 시작...")

    # 1단계: Trend Research Agent에서 트렌드 데이터 받기
    log.info("1단계 - Trend Research Agent 트렌드 분석 중...")
    trend_data = research_trends(hours=hours)

    if not trend_data:
        log.error("트렌드 데이터가 없습니다.")
        return

    # 2단계: 콘텐츠 기획 + 초안 제작
    log.info("2단계 - 콘텐츠 기획 및 초안 작성 중...")
    contents = create_contents(trend_data)

    if not contents:
        log.error("콘텐츠 생성 실패.")
        return

    # 3단계: 콘텐츠 채널로 전송
    send_message("content", f"🎨 *[Contents Creator Agent - 콘텐츠 기획안]*\n\n{contents}")

    log.info("콘텐츠 기획안 전송 완료.")
    return contents


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    run(hours=72)
