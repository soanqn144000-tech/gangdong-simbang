# -*- coding: utf-8 -*-
"""
강동교회 담임강사 심방 신청 텔레그램 봇
- 사명자가 텔레그램에서 대화형으로 심방 신청
- 웹 폼과 동일한 Firebase(visitationRequests)에 저장 → 내무부 대시보드에 실시간 반영
- python-telegram-bot v20+ 필요:  pip install python-telegram-bot requests

[설정]
1) BotFather(@BotFather)에서 새 봇 생성 → 토큰을 BOT_TOKEN에 입력
2) 실행: python simbang_bot.py
"""

import os
import threading
import http.server
import socketserver
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ============ 설정 ============
# Render 환경변수 BOT_TOKEN 에 봇 토큰을 넣어 주세요 (BotFather 발급)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
FIREBASE_URL = "https://gangdong-simbang-default-rtdb.asia-southeast1.firebasedatabase.app/visitationRequests.json"


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

# 대화 단계
NAME, PHONE, DEPT, UNIT, ROLE, HEALTH, REASON, WISH, CONFIRM = range(9)

DEPTS = ["자문회", "장년회", "부녀회", "청년회", "24부서", "신학부"]
ROLES = ["중진", "교역자", "임지역장", "교관", "팀장", "구역장"]
ROLE_LABELS = {
    "중진": "중진",
    "교역자": "교역자 (부서장·회장 포함)",
    "임지역장": "임지역장 (부서 총무 포함)",
    "교관": "교관",
    "팀장": "팀장",
    "구역장": "구역장",
}


def kb(items, prefix, cols=2):
    rows, row = [], []
    for it in items:
        row.append(InlineKeyboardButton(ROLE_LABELS.get(it, it), callback_data=f"{prefix}:{it}"))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🙏 담임강사님 심방 신청\n"
        "구역장 이상 사명자 대상 · 내무부 주관\n\n"
        "신청해 주신 내용은 내무부에서 취합하여 우선순위에 따라 "
        "심방 일정을 조율해 드립니다.\n\n"
        "먼저 성함을 입력해 주세요.\n(중단하려면 '취소' 입력)"
    )
    return NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("연락처를 입력해 주세요. (예: 010-0000-0000)")
    return PHONE


async def got_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("소속 부서를 선택해 주세요.", reply_markup=kb(DEPTS, "dept", cols=2))
    return DEPT


async def got_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["dept"] = q.data.split(":", 1)[1]
    await q.edit_message_text(f"소속 부서: {context.user_data['dept']}")
    await q.message.reply_text(
        "세부 소속을 입력해 주세요.\n"
        "(예: 3부 2팀 5구역 / 24부서는 부서명 기재)\n"
        "없으면 '없음' 이라고 보내 주세요."
    )
    return UNIT


async def got_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["unit"] = "" if t == "없음" else t
    await update.message.reply_text("직책을 선택해 주세요.", reply_markup=kb(ROLES, "role", cols=1))
    return ROLE


async def got_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["role"] = q.data.split(":", 1)[1]
    await q.edit_message_text(f"직책: {context.user_data['role']}")
    await q.message.reply_text(
        "건강 상태 (지병이 있는 경우만 기재)\n"
        "지속적인 치료나 관리가 필요한 경우에만 간단히 적어 주세요.\n"
        "기재 내용은 심방 우선순위 결정에 활용되며, 내무부에서만 확인합니다.\n\n"
        "해당 사항이 없으면 '없음' 이라고 보내 주세요."
    )
    return HEALTH


async def got_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["health"] = "" if t == "없음" else t
    await update.message.reply_text("심방을 요청하시는 사유를 적어 주세요.")
    return REASON


async def got_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reason"] = update.message.text.strip()
    await update.message.reply_text(
        "희망 시기가 있으면 적어 주세요.\n(예: 8월 중 / 가급적 빨리 / 주중 오후)\n"
        "없으면 '없음' 이라고 보내 주세요."
    )
    return WISH


async def got_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["wishDate"] = "" if t == "없음" else t
    d = context.user_data
    summary = (
        "📋 신청 내용을 확인해 주세요.\n\n"
        f"성명: {d['name']}\n"
        f"연락처: {d['phone']}\n"
        f"소속: {d['dept']} {d['unit']}".strip() + "\n"
        f"직책: {d['role']}\n"
        f"건강 상태: {d['health'] or '기재 없음'}\n"
        f"요청 사유: {d['reason']}\n"
        f"희망 시기: {d['wishDate'] or '-'}"
    )
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 제출", callback_data="confirm:yes"),
        InlineKeyboardButton("❌ 취소", callback_data="confirm:no"),
    ]])
    await update.message.reply_text(summary, reply_markup=buttons)
    return CONFIRM


async def got_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.endswith("no"):
        await q.edit_message_text("신청이 취소되었습니다. 다시 하시려면 '심방신청' 이라고 보내 주세요.")
        return ConversationHandler.END

    d = context.user_data
    import time
    payload = {
        "name": d.get("name", ""),
        "phone": d.get("phone", ""),
        "dept": d.get("dept", ""),
        "unit": d.get("unit", ""),
        "role": d.get("role", ""),
        "health": d.get("health", ""),
        "reason": d.get("reason", ""),
        "wishDate": d.get("wishDate", ""),
        "status": "신청접수",
        "memo": "",
        "source": "telegram",
        "createdAt": int(time.time() * 1000),
    }
    try:
        r = requests.post(FIREBASE_URL, json=payload, timeout=10)
        r.raise_for_status()
        await q.edit_message_text(
            "✅ 신청이 접수되었습니다.\n\n"
            "내무부에서 내용을 확인한 후 우선순위에 따라 "
            "심방 일정을 안내드리겠습니다. 감사합니다. 🙏"
        )
    except Exception:
        await q.edit_message_text(
            "⚠️ 접수 중 오류가 발생했습니다. 잠시 후 '심방신청' 으로 다시 시도해 주세요."
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("신청이 취소되었습니다. 다시 하시려면 '심방신청' 이라고 보내 주세요.")
    return ConversationHandler.END


def _cancel_handler():
    return MessageHandler(filters.Regex("^/?취소$"), cancel)


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN 환경변수가 비어 있습니다. Render 환경변수에 봇 토큰을 입력해 주세요.")
    threading.Thread(target=_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("simbang", start),
            MessageHandler(filters.Regex("^심방신청$"), start),
        ],
        states={
            NAME:    [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            PHONE:   [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_phone)],
            DEPT:    [CallbackQueryHandler(got_dept, pattern="^dept:")],
            UNIT:    [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_unit)],
            ROLE:    [CallbackQueryHandler(got_role, pattern="^role:")],
            HEALTH:  [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_health)],
            REASON:  [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_reason)],
            WISH:    [_cancel_handler(), MessageHandler(filters.TEXT & ~filters.COMMAND, got_wish)],
            CONFIRM: [CallbackQueryHandler(got_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex("^/?취소$"), cancel)],
    )
    app.add_handler(conv)
    print("simbang bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
