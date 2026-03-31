"""텔레그램 연결 테스트"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from utils.telegram_sender import send_message

print("=== 텔레그램 전송 테스트 ===\n")

result = send_message("urgent", "테스트 메시지입니다. Variational AI Agent System이 정상 연결되었습니다!")

if result:
    print("\nSUCCESS - 텔레그램 긴급 알림 채널을 확인해보세요.")
else:
    print("\nFAILED - 위의 에러 메시지를 확인해주세요.")
