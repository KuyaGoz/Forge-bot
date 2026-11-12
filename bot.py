##!/usr/bin/env python3
"""
bot.py — chat forger for TeleBotHost. Token from env TELEGRAM_BOT_TOKEN or hardcoded.
"""

import io
import os
import sys
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8744754216:AAHRH7AuMi7V-wROrsn0z5iigUarQU8rYTs")  # env wins, else paste

W, PAD, BUBBLE_FONT, NAME_FONT, LINE_H, HEADER_H = 720, 18, 26, 22, 38, 96
BG, HEADER, ME_BG, THEM_BG = (23, 33, 43), (28, 40, 51), (43, 82, 122), (32, 44, 56)
TXT, SUB = (255, 255, 255), (130, 150, 165)

LOG = logging.getLogger("forger")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(text, font, maxw, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def render_chat(title, status, messages, out_path):
    f_body, f_name, f_hdr = _font(BUBBLE_FONT), _font(NAME_FONT), _font(24)
    probe = Image.new("RGB", (W, 10))
    dtmp = ImageDraw.Draw(probe)
    max_bub = W - 2 * PAD - 80
    laid, y = [], HEADER_H + 20
    for who, text in messages:
        lines = _wrap(text, f_body, max_bub, dtmp)
        bh = LINE_H * len(lines) + 24
        bw = max(dtmp.textlength(l, font=f_body) for l in lines) + 28
        laid.append((who, lines, bw, bh, y))
        y += bh + 14
    total_h = y + 40
    img = Image.new("RGB", (W, total_h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, HEADER_H], fill=HEADER)
    d.text((PAD, 22), title, font=f_hdr, fill=TXT)
    d.text((PAD, 58), status, font=f_name, fill=SUB)
    d.line([(0, HEADER_H), (W, HEADER_H)], fill=(15, 22, 30), width=1)
    for who, lines, bw, bh, yb in laid:
        if who == "me":
            x0, x1, fill = W - PAD - bw, W - PAD, ME_BG
        else:
            x0, x1, fill = PAD, PAD + bw, THEM_BG
        d.rounded_rectangle([x0, yb, x1, yb + bh], radius=14, fill=fill)
        ty = yb + 10
        for l in lines:
            d.text((x0 + 14, ty), l, font=f_body, fill=TXT)
            ty += LINE_H
    d.text((PAD, total_h - 26), datetime.now().strftime("%H:%M"), font=f_name, fill=SUB)
    img.save(out_path, "PNG")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["msgs"] = []
    context.user_data.setdefault("title", "Chat")
    context.user_data.setdefault("status", "online")
    await update.message.reply_text(
        "chat forger up.\n\nMe: hello\nThem: hi\nMe: bye\n/done\n\n"
        "/title <name>\n/status <text>\n/reset"
    )


async def title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("usage: /title John Doe")
        return
    context.user_data["title"] = " ".join(context.args)
    await update.message.reply_text(f"title set: {context.user_data['title']}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("usage: /status last seen recently")
        return
    context.user_data["status"] = " ".join(context.args)
    await update.message.reply_text(f"status set: {context.user_data['status']}")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["msgs"] = []
    await update.message.reply_text("buffer cleared.")


async def handle_line(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if ":" not in text:
        await update.message.reply_text("format: Me: text  or  Them: text")
        return
    who_raw, body = text.split(":", 1)
    who = who_raw.strip().lower()
    if who in ("me", "you", "sender", "i"):
        who = "me"
    elif who in ("them", "other", "receiver", "he", "she", "him", "her"):
        who = "them"
    else:
        await update.message.reply_text("start line with 'Me:' or 'Them:'")
        return
    context.user_data.setdefault("msgs", []).append((who, body.strip()))
    await update.message.reply_text(f"added ({len(context.user_data['msgs'])} total)")


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msgs = context.user_data.get("msgs", [])
    if not msgs:
        await update.message.reply_text("no lines yet")
        return
    t, s = context.user_data.get("title", "Chat"), context.user_data.get("status", "online")
    tmp = f"/tmp/chat_{update.effective_user.id}.png"
    buf = io.BytesIO()
    try:
        render_chat(t, s, msgs, tmp)
        with open(tmp, "rb") as f:
            buf.write(f.read())
        buf.seek(0)
        buf.name = "chat.png"
        await update.message.reply_photo(photo=InputFile(buf, filename="chat.png"), caption=f"{len(msgs)} msgs | {t}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    context.user_data["msgs"] = []


def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        print("[!] Set TELEGRAM_BOT_TOKEN or paste token in bot.py")
        sys.exit(1)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("title", title))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_line))
    LOG.info("chat forger polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()