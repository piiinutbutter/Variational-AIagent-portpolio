"""
Market Follower Agent (Internal) 전체 파이프라인 테스트
샘플 데이터 -> Claude 분석 -> 텔레그램 전송
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from agents.market_follower_internal import run

# Variational 커뮤니티에서 수집된 것처럼 가정한 샘플 데이터
sample_data = """
[X (Twitter) 수집 데이터 - 2026.03.29]
- @crypto_kr: "Variational 새 업데이트 괜찮은데? 수수료 낮아진 거 체감됨" (좋아요 45, RT 12)
- @defi_trader_kr: "Variational UI 개선 좀.. 모바일에서 너무 불편" (좋아요 23, RT 5)
- @perp_lover: "Variational vs HyperLiquid 비교글 올림. 슬리피지는 Variational이 나음" (좋아요 89, RT 34)
- @whale_alert_kr: "Variational 거래량 어제 대비 30% 증가. 무슨 일?" (좋아요 67, RT 21)

[Discord 수집 데이터]
- 한국 채널 활성 유저: 일 평균 120명 (전주 대비 +15%)
- 주요 질문: "스테이킹 기능 언제 나오나요?", "레퍼럴 보상 구조가 어떻게 되나요?"
- 불만 사항: "출금 지연 3건 보고됨"

[Telegram 수집 데이터]
- 한국 그룹 멤버: 2,340명 (전주 대비 +80명)
- 활발한 토론: 신규 페어 상장 요청 (SOL/USDT, ARB/USDT)
- 긍정 반응: 최근 에어드롭 이벤트에 대한 호응 높음
"""

print("=== Market Follower Agent (Internal) 파이프라인 테스트 ===\n")
print("Claude에게 분석 요청 중...\n")

result = run(sample_data)

if result:
    print("\n=== 테스트 완료 ===")
else:
    print("\n=== 테스트 실패 ===")
