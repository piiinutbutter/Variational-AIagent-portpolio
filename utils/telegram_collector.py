"""
Telegram 그룹 메시지 수집 유틸리티
Telethon을 사용하여 Variational 그룹의 최근 메시지를 수집
싱글톤 클라이언트: 파이프라인 동안 하나의 연결을 재사용
"""
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from utils.logger import get_logger

log = get_logger("TG_Collector")

# 싱글톤 클라이언트 + 이벤트 루프
_client: TelegramClient | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    """이벤트 루프 싱글톤 — 매번 새로 만들지 않고 재사용"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


async def _get_client() -> TelegramClient | None:
    """텔레그램 클라이언트 싱글톤 — 한 번 연결하면 재사용"""
    global _client

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        log.error("TELEGRAM_API_ID 또는 TELEGRAM_API_HASH가 설정되지 않았습니다.")
        return None

    if _client is None or not _client.is_connected():
        _client = TelegramClient("variational_session", int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await _client.start()
        log.info("텔레그램 연결 완료 (싱글톤)")

    return _client


async def disconnect_client():
    """클라이언트 연결 해제 (파이프라인 종료 시 호출)"""
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
        _client = None
        log.info("텔레그램 연결 해제")


async def collect_messages(group_link: str, hours: int = 24, limit: int = 100) -> tuple[str, list[dict]]:
    """
    Telegram 그룹에서 최근 메시지 수집

    group_link: 그룹 유저네임 또는 초대 링크 (예: "variaboratory" 또는 "https://t.me/variaboratory")
    hours: 최근 몇 시간 내 메시지를 수집할지
    limit: 최대 수집 메시지 수
    """
    client = await _get_client()
    if not client:
        return group_link, []

    try:
        log.info(f"'{group_link}' 그룹에서 메시지 수집 중...")

        # 그룹 엔티티 가져오기
        entity = await client.get_entity(group_link)

        # 시간 필터
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        messages = []
        async for msg in client.iter_messages(entity, limit=limit):
            if msg.date < since:
                break
            if msg.text:
                text = msg.text.strip()

                # 사전 필터링: 3자 미만만 제거 (10자 이하도 키워드 포함 시 통과)
                if len(text) < 3:
                    continue
                # 봇 메시지 제거
                if msg.sender and getattr(msg.sender, "bot", False):
                    continue
                # 중복 메시지 제거
                if any(m["text"] == text[:200] for m in messages):
                    continue

                sender = "unknown"
                if msg.sender:
                    sender = getattr(msg.sender, "username", None) or getattr(msg.sender, "first_name", "unknown")

                messages.append({
                    "sender": sender,
                    "text": text,
                    "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                    "views": msg.views or 0,
                    "replies": msg.replies.replies if msg.replies else 0,
                })

        log.info(f"{len(messages)}개 메시지 수집 완료")
        return group_link, messages

    except Exception as e:
        log.error(f"Telegram 수집 실패 ({group_link}): {e}")
        return group_link, []


def collect(group_link: str, hours: int = 24, limit: int = 100) -> tuple[str, list[dict]]:
    """동기 래퍼 — 싱글톤 이벤트 루프에서 비동기 수집 실행"""
    loop = _get_loop()
    return loop.run_until_complete(collect_messages(group_link, hours, limit))


def collect_multiple(groups: list[str], hours: int = 24, limit: int = 100) -> list[tuple[str, list[dict]]]:
    """여러 그룹을 하나의 연결로 일괄 수집"""
    async def _batch():
        results = []
        for group in groups:
            result = await collect_messages(group, hours, limit)
            results.append(result)
        return results

    loop = _get_loop()
    return loop.run_until_complete(_batch())


def cleanup():
    """파이프라인 종료 시 정리 (연결 해제 + 루프 닫기)"""
    global _loop
    loop = _get_loop()
    loop.run_until_complete(disconnect_client())
    if _loop and not _loop.is_closed():
        _loop.close()
        _loop = None
    log.info("텔레그램 정리 완료")


def format_messages(group_link: str, messages: list[dict], hours: int = 24) -> str:
    """메시지 리스트를 텍스트로 포맷팅"""
    if not messages:
        return f"[Telegram] '{group_link}' 최근 {hours}시간 내 의미 있는 메시지 없음"

    output = f"[Telegram 수집 데이터 - 그룹: {group_link}]\n"
    output += f"총 {len(messages)}개 메시지 (필터링 후)\n\n"

    for m in messages:
        output += (
            f"- @{m['sender']} ({m['date']}): \"{m['text'][:200]}\" "
            f"(views: {m['views']}, replies: {m['replies']})\n"
        )

    return output


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    # 테스트: Variational 그룹 유저네임을 넣어서 실행
    group, messages = collect("variational_io_KR", hours=168, limit=30)
    print(format_messages(group, messages, hours=168))
    cleanup()
