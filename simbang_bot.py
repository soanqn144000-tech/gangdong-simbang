# -*- coding: utf-8 -*-
"""
강동교회 담임강사 심방 신청 텔레그램 봇 (미니앱 방식)
- /start 또는 아무 메시지 -> [심방 신청하기] 버튼
- 버튼을 누르면 텔레그램 안에서 신청 폼이 팝업으로 열림 (Telegram Mini App)
- 폼 제출 시 웹과 동일한 Firebase(visitationRequests)에 저장 -> 내무부 대시보드 실시간 반영
"""

import os
import threading
import http.server
import socketserver
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = "https://soanqn144000-tech.github.io/gangdong-simbang/"


def _health_server():
    """Render 무료 웹서비스 유지용 (UptimeRobot 핑 응답)"""
    port = int(os.environ.get("PORT", "10000"))

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"simbang bot alive")

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()

        def log_message(self, *a):
            pass

    with socketserver.TCPServer(("", port), H) as httpd:
        httpd.serve_forever()


WELCOME = (
    "🙏 담임강사님 심방 신청\n"
    "구역장 이상 사명자 대상 · 내무부 주관\n\n"
    "아래 [심방 신청하기] 버튼을 누르시면\n"
    "신청서가 열립니다.\n\n"
    "신청해 주신 내용은 내무부에서 취합하여\n"
    "우선순위에 따라 심방 일정을 조율해 드립니다."
)


def _kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 심방 신청하기", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=_kb())


async def any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "아래 버튼을 눌러 심방 신청서를 열어 주세요.", reply_markup=_kb()
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN 환경변수가 비어 있습니다.")
    threading.Thread(target=_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("simbang", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_text))
    print("simbang bot running (webapp mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
