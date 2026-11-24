# -*- coding: utf-8 -*-
"""
강동교회 담임강사 심방 신청 텔레그램 봇 (미니앱 방식)
- /start 또는 아무 메시지 -> [심방 신청하기] 버튼
- 버튼을 누르면 텔레그램 안에서 신청 폼이 팝업으로 열림 (Telegram Mini App)
- 폼 제출 시 웹과 동일한 Firebase(visitationRequests)에 저장 -> 내무부 대시보드 실시간 반영
"""

import os
import time
import asyncio
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


def _build():
    app = (Application.builder().token(BOT_TOKEN)
           .connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
           .get_updates_connect_timeout(30).get_updates_read_timeout(40)
           .build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("simbang", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_text))
    return app


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN 환경변수가 비어 있습니다.")
    # 포트는 한 번만 연다 — 봇이 재시도하는 동안에도 Render 는 살아 있다고 본다
    threading.Thread(target=_health_server, daemon=True).start()

    # 2026-11-24: 켜질 때 텔레그램 접속이 늦으면(TimedOut) 프로세스가 죽고,
    # 재시작이 반복되다 Flood control 에 걸려 봇이 멈췄다 → 죽지 말고 기다렸다 다시 붙는다
    wait = 5
    while True:
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            print("simbang bot running (webapp mode)...", flush=True)
            _build().run_polling(bootstrap_retries=-1, close_loop=False)
            return
        except Exception as e:
            print(f"bot error: {type(e).__name__}: {e} -> {wait}s 뒤 다시", flush=True)
            time.sleep(wait)
            wait = min(wait * 2, 300)


if __name__ == "__main__":
    main()
