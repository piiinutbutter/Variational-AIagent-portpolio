"""
이메일 전송 유틸리티
POC Agent가 상사에게 보고서를 보낼 때 사용
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import EMAIL_CONFIG
from utils.logger import get_logger

log = get_logger("Email")


def send_email(subject: str, body: str):
    """
    이메일 전송

    subject: 메일 제목
    body: 메일 본문 (HTML 가능)
    """
    config = EMAIL_CONFIG

    if not config["username"] or not config["password"]:
        log.error("이메일 설정이 없습니다. .env 파일을 확인하세요.")
        return False

    msg = MIMEMultipart()
    msg["From"] = config["username"]
    msg["To"] = config["recipient"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(config["smtp_host"], config["smtp_port"])
        server.starttls()
        server.login(config["username"], config["password"])
        server.send_message(msg)
        server.quit()
        log.info(f"이메일 전송 완료: {subject}")
        return True
    except Exception as e:
        log.error(f"이메일 전송 실패: {e}")
        return False
