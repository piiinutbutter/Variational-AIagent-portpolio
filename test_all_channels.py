"""모든 텔레그램 채널 전송 테스트"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from utils.telegram_sender import send_message

channels = {
    "urgent": "긴급 알림 채널",
    "market": "시장 분석 채널",
    "content": "콘텐츠 채널",
    "performance": "성과+종합보고 채널",
    "qa_marketing": "Q&A+마케팅 채널",
}

print("=== 전체 채널 전송 테스트 ===\n")

for key, name in channels.items():
    result = send_message(key, f"[{name}] 테스트 메시지입니다. 정상 연결 확인!")
    status = "OK" if result else "FAIL"
    print(f"  {name}: {status}")

print("\n=== 테스트 완료 ===")
