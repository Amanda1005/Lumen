"""
Lumen Telegram Alerts Bot.
Provides agent lookup and sybil alert subscriptions via Telegram.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AGENTS_FILE = Path("data/agents_with_comments.json")
SUBSCRIBERS_FILE = Path("data/telegram_subscribers.json")


# ============================================================
# Data helpers
# ============================================================

def load_agents() -> list[dict]:
    if not AGENTS_FILE.exists():
        return []
    with open(AGENTS_FILE) as f:
        return json.load(f)


def load_subscribers() -> set[int]:
    if not SUBSCRIBERS_FILE.exists():
        return set()
    with open(SUBSCRIBERS_FILE) as f:
        return set(json.load(f))


def save_subscribers(subs: set[int]) -> None:
    SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)


def find_agent(agent_id: int) -> dict | None:
    for a in load_agents():
        if a["agent_id"] == agent_id:
            return a
    return None


# ============================================================
# Handlers
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "Welcome to Lumen Alerts.\n\n"
        "Lumen is an institutional-grade rating system for AI agents on Mantle.\n\n"
        "Available commands:\n"
        "/subscribe - Get notified when new sybil agents are detected\n"
        "/unsubscribe - Stop receiving alerts\n"
        "/latest - Show 5 most recent sybil agents\n"
        "/check <id> - Look up an agent by ID (e.g. /check 95)\n"
        "/stats - Ecosystem summary\n"
        "/help - Show this message"
    )
    await update.message.reply_text(msg)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    if chat_id in subs:
        await update.message.reply_text("You are already subscribed.")
        return
    subs.add(chat_id)
    save_subscribers(subs)
    await update.message.reply_text(
        "Subscribed. You will receive alerts when new sybil agents are detected."
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = load_subscribers()
    if chat_id not in subs:
        await update.message.reply_text("You are not subscribed.")
        return
    subs.discard(chat_id)
    save_subscribers(subs)
    await update.message.reply_text("Unsubscribed.")


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    agents = load_agents()
    sybils = [a for a in agents if a.get("risk_level") == "SYBIL"]
    sybils.sort(key=lambda a: a["agent_id"], reverse=True)
    top5 = sybils[:5]

    if not top5:
        await update.message.reply_text("No sybil agents detected.")
        return

    lines = ["Latest sybil agents detected:\n"]
    for a in top5:
        lines.append(
            f"#{a['agent_id']} {a['name']}\n"
            f"   Score: {a['lumen_score']} (Grade {a['grade']})\n"
            f"   Owner: {a['owner'][:10]}...{a['owner'][-6:]}\n"
        )
    await update.message.reply_text("\n".join(lines))


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /check <agent_id>\nExample: /check 95")
        return

    try:
        agent_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Agent ID must be a number.")
        return

    agent = find_agent(agent_id)
    if not agent:
        await update.message.reply_text(f"Agent #{agent_id} not found.")
        return

    risk_label = {
        "SAFE": "SAFE",
        "SUSPICIOUS": "SUSPICIOUS",
        "SYBIL": "SYBIL (high risk)",
    }.get(agent.get("risk_level"), "UNKNOWN")

    msg = (
        f"Agent #{agent['agent_id']} {agent['name']}\n"
        f"---------------------------------\n"
        f"Lumen Score: {agent['lumen_score']} (Grade {agent['grade']})\n"
        f"Risk Level:  {risk_label}\n"
        f"Owner:       {agent['owner']}\n"
    )

    note = agent.get("analyst_note")
    if note:
        msg += f"\nAnalyst note:\n{note}\n"

    await update.message.reply_text(msg)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    agents = load_agents()
    total = len(agents)
    safe = sum(1 for a in agents if a.get("risk_level") == "SAFE")
    sybil = sum(1 for a in agents if a.get("risk_level") == "SYBIL")
    avg = round(sum(a["lumen_score"] for a in agents) / total, 1) if total else 0

    msg = (
        "Lumen Ecosystem Summary\n"
        "---------------------------------\n"
        f"Total agents:  {total}\n"
        f"Safe agents:   {safe}\n"
        f"Sybil agents:  {sybil} ({round(sybil/total*100, 1)}%)\n"
        f"Average score: {avg}\n"
        "\nSource: Mantle Mainnet ERC-8004 IdentityRegistry"
    )
    await update.message.reply_text(msg)


# ============================================================
# Main
# ============================================================

def main() -> None:
    if not TOKEN:
        print("Missing TELEGRAM_BOT_TOKEN in backend/.env")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("stats", stats))

    print("Lumen Telegram Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()