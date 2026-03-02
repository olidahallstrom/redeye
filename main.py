#!/usr/bin/env python3
"""
Red Eye Cookies Bot — v2
Render.com Webhook Deployment

New in v2:
  • Cookie types: Yahoo, AOL, Office 365, Google Suite
  • Redirect Link service: Redirect Link ($100/mo) or Source Code ($75/mo)
  • URL input flow via text message handler
  • Updated welcome message
  • Admin: /deliver_rl command
"""
import asyncio
import sys

if sys.version_info >= (3, 10):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
#  CONFIG
# ============================================================
BOT_TOKEN   = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
ADMIN_ID    = int(os.environ["ADMIN_ID"])
PORT        = int(os.environ.get("PORT", 8080))
SUPPORT_UN  = os.environ.get("SUPPORT_UN",  "@support")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/channel")
CRYPTO_ADDR = os.environ.get("CRYPTO_ADDR", "SET_YOUR_BTC_ADDRESS")
USDT_ADDR   = os.environ.get("USDT_ADDR",   "SET_YOUR_USDT_ADDRESS")

WEBHOOK_PATH = BOT_TOKEN

# ============================================================
#  USER-DATA STATE KEYS  (per-user, stored in context.user_data)
# ============================================================
UD_COOKIE_TYPE  = "cookie_type"
UD_RL_TYPE      = "rl_type"
UD_AWAITING_URL = "awaiting_rl_url"
UD_RL_URL       = "rl_target_url"

# ============================================================
#  IN-MEMORY ORDER STORE
#  Swap for PostgreSQL (Render add-on) in production
# ============================================================
user_orders: dict   = {}
order_counter: list = [0]


def next_order_id(user_id: int) -> str:
    order_counter[0] += 1
    return f"ORD-{user_id}-{order_counter[0]:05d}"


# ============================================================
#  COOKIE TYPES
# ============================================================
COOKIE_TYPES = {
    "yahoo":  {"name": "Yahoo",        "emoji": "🟣"},
    "aol":    {"name": "AOL",          "emoji": "🔵"},
    "office": {"name": "Office 365",   "emoji": "🟦"},
    "gsuite": {"name": "Google Suite", "emoji": "🔴"},
}

# ============================================================
#  REDIRECT TYPES
# ============================================================
REDIRECT_TYPES = {
    "link": {"name": "Redirect Link",  "emoji": "🔗", "price": "$100.00"},
    "code": {"name": "Source Code",    "emoji": "💻", "price": "$75.00"},
}

# ============================================================
#  COOKIE SUBSCRIPTION PLANS
# ============================================================
PLANS = {
    # ── WEEKLY ──────────────────────────────────────────────
    "wk_basic": {
        "name": "Weekly Basic", "tier": "WEEKLY",
        "duration": "7 Days",   "price": "$9.99", "emoji": "🟢",
        "features": [
            "1 Active Account",
            "Browser‑in‑Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "wk_pro": {
        "name": "Weekly Pro", "tier": "WEEKLY",
        "duration": "7 Days",  "price": "$14.99", "emoji": "🔵",
        "features": [
            "3 Active Accounts",
            "Browser‑in‑Browser Support",
            "Email + Background Logo",
            "Long‑Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    # ── BI-WEEKLY ────────────────────────────────────────────
    "bw_basic": {
        "name": "Bi‑Weekly Basic", "tier": "BI‑WEEKLY",
        "duration": "14 Days",     "price": "$17.99", "emoji": "🟡",
        "features": [
            "1 Active Account",
            "Browser‑in‑Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "bw_pro": {
        "name": "Bi‑Weekly Pro", "tier": "BI‑WEEKLY",
        "duration": "14 Days",   "price": "$24.99", "emoji": "🟠",
        "features": [
            "5 Active Accounts",
            "Browser‑in‑Browser Support",
            "Email + Background Logo",
            "Long‑Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    # ── MONTHLY ──────────────────────────────────────────────
    "mo_basic": {
        "name": "Monthly Basic", "tier": "MONTHLY",
        "duration": "30 Days",   "price": "$29.99", "emoji": "🔴",
        "features": [
            "1 Active Account",
            "Browser‑in‑Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "mo_pro": {
        "name": "Monthly Pro", "tier": "MONTHLY",
        "duration": "30 Days",  "price": "$44.99", "emoji": "⚡",
        "features": [
            "10 Active Accounts",
            "Browser‑in‑Browser Support",
            "Email + Background Logo",
            "Long‑Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    "mo_elite": {
        "name": "Monthly Elite", "tier": "MONTHLY",
        "duration": "30 Days",   "price": "$69.99", "emoji": "👑",
        "features": [
            "Unlimited Accounts",
            "Browser‑in‑Browser Support",
            "Email + Background Logo",
            "Maximum Cookie Stability",
            "VIP 24/7 Support",
            "Instant Telegram Delivery",
        ],
    },
}


# ============================================================
#  KEYBOARD BUILDERS
# ============================================================

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍪  Cookies",         callback_data="cookies_menu"),
         InlineKeyboardButton("🔗  Redirect Links",  callback_data="redirect_menu")],
        [InlineKeyboardButton("🛒  Buy Now",         callback_data="buy_now"),
         InlineKeyboardButton("📋  Plans & Pricing", callback_data="plans")],
        [InlineKeyboardButton("📊  My Dashboard",    callback_data="dashboard"),
         InlineKeyboardButton("🎫  My Orders",       callback_data="my_orders")],
        [InlineKeyboardButton("💬  Support",         callback_data="support"),
         InlineKeyboardButton("ℹ️  About",           callback_data="about")],
        [InlineKeyboardButton("📢  Our Channel",     url=CHANNEL_URL)],
    ])


def kb_cookies_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  SELECT COOKIE TYPE  ━━━", callback_data="noop")],
        [InlineKeyboardButton("🟣  Yahoo",        callback_data="cookie_yahoo"),
         InlineKeyboardButton("🔵  AOL",          callback_data="cookie_aol")],
        [InlineKeyboardButton("🟦  Office 365",   callback_data="cookie_office"),
         InlineKeyboardButton("🔴  Google Suite", callback_data="cookie_gsuite")],
        [InlineKeyboardButton("🔙  Main Menu",    callback_data="main_menu")],
    ])


def kb_redirect_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  SELECT OUTPUT TYPE  ━━━",    callback_data="noop")],
        [InlineKeyboardButton("🔗  Redirect Link  —  $100/mo",   callback_data="rl_select_link")],
        [InlineKeyboardButton("💻  Source Code    —  $75/mo",    callback_data="rl_select_code")],
        [InlineKeyboardButton("🔙  Main Menu",                   callback_data="main_menu")],
    ])


def kb_plans_for_cookie(cookie_type: str) -> InlineKeyboardMarkup:
    px = f"cplan_{cookie_type}_"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  WEEKLY PLANS  ━━━",   callback_data="noop")],
        [InlineKeyboardButton("🟢 Basic  $9.99",  callback_data=f"{px}wk_basic"),
         InlineKeyboardButton("🔵 Pro  $14.99",   callback_data=f"{px}wk_pro")],
        [InlineKeyboardButton("━━  BI‑WEEKLY PLANS  ━━",  callback_data="noop")],
        [InlineKeyboardButton("🟡 Basic  $17.99", callback_data=f"{px}bw_basic"),
         InlineKeyboardButton("🟠 Pro  $24.99",   callback_data=f"{px}bw_pro")],
        [InlineKeyboardButton("━━━  MONTHLY PLANS  ━━━",  callback_data="noop")],
        [InlineKeyboardButton("🔴 Basic  $29.99", callback_data=f"{px}mo_basic"),
         InlineKeyboardButton("⚡ Pro  $44.99",   callback_data=f"{px}mo_pro")],
        [InlineKeyboardButton("👑  Elite  $69.99  — BEST VALUE", callback_data=f"{px}mo_elite")],
        [InlineKeyboardButton("🔙  Back",          callback_data="cookies_menu")],
    ])


def kb_plans_generic() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  WEEKLY PLANS  ━━━",    callback_data="noop")],
        [InlineKeyboardButton("🟢 Basic  $9.99",  callback_data="plan_wk_basic"),
         InlineKeyboardButton("🔵 Pro  $14.99",   callback_data="plan_wk_pro")],
        [InlineKeyboardButton("━━  BI‑WEEKLY PLANS  ━━",   callback_data="noop")],
        [InlineKeyboardButton("🟡 Basic  $17.99", callback_data="plan_bw_basic"),
         InlineKeyboardButton("🟠 Pro  $24.99",   callback_data="plan_bw_pro")],
        [InlineKeyboardButton("━━━  MONTHLY PLANS  ━━━",   callback_data="noop")],
        [InlineKeyboardButton("🔴 Basic  $29.99", callback_data="plan_mo_basic"),
         InlineKeyboardButton("⚡ Pro  $44.99",   callback_data="plan_mo_pro")],
        [InlineKeyboardButton("👑  Elite  $69.99  — BEST VALUE", callback_data="plan_mo_elite")],
        [InlineKeyboardButton("🔙 Back",           callback_data="main_menu")],
    ])


def kb_plan_detail(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase This Plan", callback_data=f"buy_{plan_key}")],
        [InlineKeyboardButton("📋  All Plans", callback_data="plans"),
         InlineKeyboardButton("🔙  Menu",      callback_data="main_menu")],
    ])


def kb_cplan_detail(cookie_type: str, plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase This Plan", callback_data=f"cbuy_{cookie_type}_{plan_key}")],
        [InlineKeyboardButton("📋  All Plans", callback_data=f"cookie_{cookie_type}"),
         InlineKeyboardButton("🔙  Menu",      callback_data="main_menu")],
    ])


def kb_payment_generic(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"pay_btc_{plan_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"pay_usdt_{plan_key}")],
        [InlineKeyboardButton("🔙  Back to Plans",       callback_data="plans")],
    ])


def kb_cpayment(cookie_type: str, plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"cpay_btc_{cookie_type}_{plan_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"cpay_usdt_{cookie_type}_{plan_key}")],
        [InlineKeyboardButton("🔙  Back",                callback_data=f"cookie_{cookie_type}")],
    ])


def kb_rl_payment() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data="rl_pay_btc")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data="rl_pay_usdt")],
        [InlineKeyboardButton("❌  Cancel",              callback_data="main_menu")],
    ])


def kb_support() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆘  Open Ticket", callback_data="open_ticket")],
        [InlineKeyboardButton("📖  FAQ",          callback_data="faq"),
         InlineKeyboardButton("💬  Live Chat",    url=f"https://t.me/{SUPPORT_UN.lstrip('@')}")],
        [InlineKeyboardButton("🔙  Main Menu",    callback_data="main_menu")],
    ])


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙  Main Menu", callback_data="main_menu")]
    ])


# ============================================================
#  MESSAGE TEMPLATES
# ============================================================

WELCOME = """\
🍪🔗 *Welcome to Red Eye Cookies Bot\\!* 🔗🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 *Your \\#1 Source for Premium Digital Tools*

🍪 *COOKIE SERVICE*
🟣 Yahoo  \\|  🔵 AOL  \\|  🟦 Office 365  \\|  🔴 GSuite
✅  Browser‑in‑Browser Full Session Support
✅  Background Logo \\& Email Access Included
✅  Long‑Lasting Stability — Zero Drop‑Offs
✅  Results Delivered Instantly via Telegram

🔗 *REDIRECT LINK SERVICE — NEW\\!*
✅  Submit Any URL → Receive a Clean Cloaked Link
✅  Or Get Full Source Code to Self‑Host
✅  Anti‑Detection Cloaking Built‑In on All Outputs
✅  Lightning‑Fast Turnaround After Payment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 *COOKIE PLANS FROM \\$9\\.99/wk*
🟢 Weekly  \\|  🟡 Bi‑Weekly  \\|  👑 Monthly Elite

🔗 Redirect Link: *\\$100/mo*   ╏   💻 Source Code: *\\$75/mo*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ *Fully Encrypted  \\|  24\\/7 Support  \\|  Zero Logs*

👇 *Tap an option below to get started\\!*\
"""

ABOUT_MSG = """\
🍪 *About Red Eye Cookies* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 *Why Choose Us?*

🍪 *Cookie Service*
🟣  Yahoo — Fresh \\& Stable Sessions
🔵  AOL — Reliable Long‑Term Cookies
🟦  Office 365 — Full Business Account Access
🔴  Google Suite — Enterprise‑Grade Workspace

🔗 *Redirect Link Service*
🔗  Clean Redirect Links — Ready to Deploy Instantly
💻  Full Source Code — Host It Your Own Way
🛡️  Anti‑Detection Cloaking on Every Output

📦 *7 Cookie Plans* — Weekly, Bi‑Weekly \\& Monthly
🔐 *Fast \\& Secure* — Instant Telegram delivery
🌐 *Browser‑in‑Browser* — Full session compatibility
⏳ *Long‑Lasting Cookies* — Maximum stability
🛡️ *24/7 Support* — Always here when you need us
📲 *User Dashboard* — Manage all orders in one place

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Questions? Hit Support below\\!\
"""


# ============================================================
#  /start
# ============================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # Clear any lingering state
    ctx.user_data.pop(UD_AWAITING_URL, None)
    ctx.user_data.pop(UD_RL_TYPE, None)
    ctx.user_data.pop(UD_RL_URL, None)
    ctx.user_data.pop(UD_COOKIE_TYPE, None)
    logger.info("CMD /start — uid=%s @%s", user.id, user.username)
    await update.message.reply_text(
        WELCOME, parse_mode="MarkdownV2", reply_markup=kb_main()
    )


# ============================================================
#  TEXT MESSAGE HANDLER  (Redirect URL input)
# ============================================================

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Collects the target URL for the Redirect Link service."""
    if not ctx.user_data.get(UD_AWAITING_URL):
        # Not in URL-collection state — just show the menu
        await update.message.reply_text(
            "👇 Use the menu below to navigate:", reply_markup=kb_main()
        )
        return

    url     = update.message.text.strip()
    rl_type = ctx.user_data.get(UD_RL_TYPE, "link")
    rt      = REDIRECT_TYPES[rl_type]

    # Persist URL; clear awaiting flag
    ctx.user_data[UD_RL_URL]       = url
    ctx.user_data[UD_AWAITING_URL] = False

    msg = (
        f"🔗 *Redirect Order Preview*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{rt['emoji']}  *Output Type:*  {rt['name']}\n"
        f"💵  *Price:*       {rt['price']} / month\n\n"
        f"🌐  *Target URL:*\n"
        f"`{url}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ URL received\\!  Select payment method 👇"
    )
    await update.message.reply_text(
        msg, parse_mode="MarkdownV2", reply_markup=kb_rl_payment()
    )


# ============================================================
#  CALLBACK ROUTER
# ============================================================

async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    d = q.data

    # ── NOOP (section headers) ──────────────────────────────
    if d == "noop":
        return

    # ── MAIN MENU ───────────────────────────────────────────
    elif d == "main_menu":
        ctx.user_data.pop(UD_AWAITING_URL, None)
        await q.edit_message_text(
            WELCOME, parse_mode="MarkdownV2", reply_markup=kb_main()
        )

    # ────────────────────────────────────────────────────────
    #  COOKIE FLOWS
    # ────────────────────────────────────────────────────────

    # ── COOKIES MAIN MENU ───────────────────────────────────
    elif d == "cookies_menu":
        msg = (
            "🍪 *Cookie Service* 🍪\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select the type of cookies you need:\n\n"
            "🟣 *Yahoo* — Email & account sessions\n"
            "🔵 *AOL* — Stable, long‑lasting sessions\n"
            "🟦 *Office 365* — Full MS business access\n"
            "🔴 *Google Suite* — Enterprise workspace\n\n"
            "Every type includes:\n"
            "✅ Browser‑in‑Browser Support\n"
            "✅ Email + Logo Grab\n"
            "✅ Instant Telegram Delivery\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 Choose a type below:"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_cookies_menu())

    # ── INDIVIDUAL COOKIE TYPE ──────────────────────────────
    elif d.startswith("cookie_"):
        ctype = d[7:]                       # "yahoo" | "aol" | "office" | "gsuite"
        ct    = COOKIE_TYPES.get(ctype)
        if not ct:
            return
        ctx.user_data[UD_COOKIE_TYPE] = ctype
        msg = (
            f"{ct['emoji']} *{ct['name']} Cookies — Choose Your Plan* {ct['emoji']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Each plan includes:\n"
            f"✅ {ct['name']} Session Cookies\n"
            "✅ Browser‑in‑Browser Support\n"
            "✅ Email & Background Logo\n"
            "✅ 24/7 Priority Support\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_plans_for_cookie(ctype)
        )

    # ── COOKIE PLAN DETAIL  cplan_{ctype}_{plankey} ─────────
    elif d.startswith("cplan_"):
        # e.g. "cplan_yahoo_wk_basic"  →  rest="yahoo_wk_basic"
        rest  = d[6:]
        parts = rest.split("_", 1)          # ["yahoo", "wk_basic"]
        if len(parts) < 2:
            return
        ctype, plan_key = parts[0], parts[1]
        p  = PLANS.get(plan_key)
        ct = COOKIE_TYPES.get(ctype)
        if not p or not ct:
            return
        feats = "\n".join(f"   ✅ {f}" for f in p["features"])
        msg = (
            f"{ct['emoji']} {p['emoji']} *{ct['name']} — {p['name']}* {p['emoji']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱  *Duration:* {p['duration']}\n"
            f"💵  *Price:*    {p['price']}\n"
            f"📦  *Tier:*     {p['tier']}\n\n"
            f"🗂 *What's Included:*\n{feats}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Delivery: Instant to Telegram\n"
            f"🔐 Fully Encrypted Transfer\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_cplan_detail(ctype, plan_key)
        )

    # ── COOKIE CHECKOUT  cbuy_{ctype}_{plankey} ─────────────
    elif d.startswith("cbuy_"):
        rest  = d[5:]
        parts = rest.split("_", 1)
        if len(parts) < 2:
            return
        ctype, plan_key = parts[0], parts[1]
        p  = PLANS.get(plan_key)
        ct = COOKIE_TYPES.get(ctype)
        if not p or not ct:
            return
        msg = (
            f"💳 *Checkout — {ct['name']} {p['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ct['emoji']}  Cookie Type:  {ct['name']}\n"
            f"📦  Plan:        {p['name']}\n"
            f"⏱   Duration:   {p['duration']}\n"
            f"💵  Amount:      *{p['price']}*\n\n"
            f"Select your payment method below 👇\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_cpayment(ctype, plan_key)
        )

    # ── COOKIE PAYMENT  cpay_btc/usdt_{ctype}_{plankey} ─────
    # NOTE: these must be checked BEFORE the generic pay_btc_ / pay_usdt_ branches
    elif d.startswith("cpay_btc_") or d.startswith("cpay_usdt_"):
        if d.startswith("cpay_btc_"):
            method, addr, rest = "BTC", CRYPTO_ADDR, d[9:]
        else:
            method, addr, rest = "USDT (TRC20)", USDT_ADDR, d[10:]

        parts = rest.split("_", 1)
        if len(parts) < 2:
            return
        ctype, plan_key = parts[0], parts[1]
        p  = PLANS.get(plan_key)
        ct = COOKIE_TYPES.get(ctype)
        if not p or not ct:
            return

        user = q.from_user
        oid  = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":     user.id,
            "username":    user.username or "N/A",
            "plan_key":    plan_key,
            "plan":        f"{ct['name']} — {p['name']}",
            "cookie_type": ctype,
            "price":       p["price"],
            "method":      method,
            "status":      "Pending",
            "order_type":  "cookie",
        }

        msg = (
            f"📝 *Order Created Successfully\\!* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Order ID:    `{oid}`\n"
            f"{ct['emoji']}  Cookie Type: {ct['name']}\n"
            f"📦  Plan:        {p['name']}\n"
            f"💵  Amount:      {p['price']}\n"
            f"💳  Method:      {method}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Send Exact Amount To:*\n"
            f"`{addr}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *After Payment — 3 Steps:*\n"
            f"1️⃣  Screenshot or copy TX hash\n"
            f"2️⃣  Message {SUPPORT_UN} with Order ID\n"
            f"3️⃣  Cookies delivered in *5–15 min* ✅\n\n"
            f"⚠️  Order expires in *30 minutes*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🔔 *NEW COOKIE ORDER*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username or 'N/A'}  \\(`{user.id}`\\)\n"
                f"{ct['emoji']}  {ct['name']} Cookies\n"
                f"📦  {p['name']}\n"
                f"💵  {p['price']}\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ `/complete {oid}` to confirm\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ────────────────────────────────────────────────────────
    #  REDIRECT LINK FLOWS
    # ────────────────────────────────────────────────────────

    # ── REDIRECT MAIN MENU ──────────────────────────────────
    elif d == "redirect_menu":
        msg = (
            "🔗 *Redirect Link Service* 🔗\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Turn *any URL* into a clean, cloaked redirect.\n\n"
            "🔗 *Redirect Link — $100/month*\n"
            "   ✅ Submit your URL, get a ready-to-use link\n"
            "   ✅ Hosted & managed — zero setup required\n"
            "   ✅ Anti-detection cloaking built-in\n\n"
            "💻 *Source Code — $75/month*\n"
            "   ✅ Full PHP/HTML source code delivered\n"
            "   ✅ Host on your own server\n"
            "   ✅ 100% customisable output\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 Choose your output type:"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_redirect_menu()
        )

    # ── REDIRECT TYPE SELECTED → prompt for URL ─────────────
    elif d in ("rl_select_link", "rl_select_code"):
        rl_type = "link" if d == "rl_select_link" else "code"
        rt = REDIRECT_TYPES[rl_type]
        ctx.user_data[UD_RL_TYPE]      = rl_type
        ctx.user_data[UD_AWAITING_URL] = True

        msg = (
            f"{rt['emoji']} *{rt['name']}*  —  {rt['price']}/mo\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📎 *Please type your target URL in the chat below\\.*\n\n"
            f"Example:\n"
            f"`https://example\\.com/landing\\-page`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Waiting for your URL\\.\\.\\."
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

    # ── REDIRECT PAYMENT (triggered after handle_text) ──────
    elif d in ("rl_pay_btc", "rl_pay_usdt"):
        rl_type = ctx.user_data.get(UD_RL_TYPE, "link")
        rl_url  = ctx.user_data.get(UD_RL_URL, "N/A")
        rt      = REDIRECT_TYPES[rl_type]
        method  = "BTC" if d == "rl_pay_btc" else "USDT (TRC20)"
        addr    = CRYPTO_ADDR if d == "rl_pay_btc" else USDT_ADDR

        user = q.from_user
        oid  = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":    user.id,
            "username":   user.username or "N/A",
            "plan_key":   f"rl_{rl_type}",
            "plan":       f"Redirect — {rt['name']}",
            "price":      rt["price"],
            "method":     method,
            "status":     "Pending",
            "order_type": "redirect",
            "rl_type":    rl_type,
            "rl_url":     rl_url,
        }
        # Clear redirect state
        ctx.user_data.pop(UD_AWAITING_URL, None)
        ctx.user_data.pop(UD_RL_TYPE, None)
        ctx.user_data.pop(UD_RL_URL, None)

        msg = (
            f"📝 *Redirect Order Created\\!* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Order ID:  `{oid}`\n"
            f"{rt['emoji']}  Type:      {rt['name']}\n"
            f"💵  Amount:    {rt['price']}\n"
            f"💳  Method:    {method}\n"
            f"🌐  Target:    `{rl_url}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Send Exact Amount To:*\n"
            f"`{addr}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *After Payment — 3 Steps:*\n"
            f"1️⃣  Screenshot or copy TX hash\n"
            f"2️⃣  Message {SUPPORT_UN} with Order ID\n"
            f"3️⃣  Redirect delivered in *5–15 min* ✅\n\n"
            f"⚠️  Order expires in *30 minutes*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🔔 *NEW REDIRECT ORDER*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username or 'N/A'}  \\(`{user.id}`\\)\n"
                f"{rt['emoji']}  {rt['name']}\n"
                f"💵  {rt['price']}\n"
                f"💳  {method}\n"
                f"🌐  `{rl_url}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ `/complete {oid}` when confirmed\\.\n"
                f"📤 `/deliver\\_rl {oid} <result>` to send output\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ────────────────────────────────────────────────────────
    #  GENERIC COOKIE PLANS FLOW  (Buy Now / Plans & Pricing)
    # ────────────────────────────────────────────────────────

    elif d in ("buy_now", "plans"):
        hdr = "🛒 *Buy Now — Pick Your Plan*" if d == "buy_now" else "📋 *Plans & Pricing*"
        msg = (
            f"{hdr}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Every plan includes:\n"
            "✅ Browser‑in‑Browser  ✅ Telegram Delivery\n"
            "✅ Email \\+ Logo Access ✅ 24/7 Support\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="MarkdownV2", reply_markup=kb_plans_generic()
        )

    elif d.startswith("plan_"):
        key = d[5:]
        p   = PLANS.get(key)
        if not p:
            return
        feats = "\n".join(f"   ✅ {f}" for f in p["features"])
        msg = (
            f"{p['emoji']} *{p['name']}* {p['emoji']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱  *Duration:* {p['duration']}\n"
            f"💵  *Price:*    {p['price']}\n"
            f"📦  *Tier:*     {p['tier']}\n\n"
            f"🗂 *What's Included:*\n{feats}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Delivery: Instant to Telegram\n"
            f"🔐 Fully Encrypted Transfer\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_plan_detail(key)
        )

    elif d.startswith("buy_"):
        key = d[4:]
        p   = PLANS.get(key)
        if not p:
            return
        msg = (
            f"💳 *Checkout — {p['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Plan:     {p['name']}\n"
            f"⏱  Duration: {p['duration']}\n"
            f"💵 Amount:   *{p['price']}*\n\n"
            f"Select your payment method below 👇\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_payment_generic(key)
        )

    elif d.startswith("pay_btc_") or d.startswith("pay_usdt_"):
        if d.startswith("pay_btc_"):
            method, key, addr = "BTC", d[8:], CRYPTO_ADDR
        else:
            method, key, addr = "USDT (TRC20)", d[9:], USDT_ADDR

        p = PLANS.get(key)
        if not p:
            return

        user = q.from_user
        oid  = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":    user.id,
            "username":   user.username or "N/A",
            "plan_key":   key,
            "plan":       p["name"],
            "price":      p["price"],
            "method":     method,
            "status":     "Pending",
            "order_type": "cookie",
        }

        msg = (
            f"📝 *Order Created Successfully\\!* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Order ID:  `{oid}`\n"
            f"📦  Plan:      {p['name']}\n"
            f"💵  Amount:    {p['price']}\n"
            f"💳  Method:    {method}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Send Exact Amount To:*\n"
            f"`{addr}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *After Payment — 3 Steps:*\n"
            f"1️⃣  Screenshot or copy TX hash\n"
            f"2️⃣  Message {SUPPORT_UN} with Order ID\n"
            f"3️⃣  Cookies delivered in *5–15 min* ✅\n\n"
            f"⚠️  Order expires in *30 minutes*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🔔 *NEW ORDER*\n"
                f"━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username or 'N/A'}  \\(`{user.id}`\\)\n"
                f"📦  {p['name']}\n"
                f"💵  {p['price']}\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━\n"
                f"✅ Use `/complete {oid}` when confirmed\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ────────────────────────────────────────────────────────
    #  DASHBOARD / ORDERS / SUPPORT / ABOUT
    # ────────────────────────────────────────────────────────

    elif d == "dashboard":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]
        total  = len(orders)
        done   = sum(1 for _, o in orders if o["status"] == "Completed")

        recent_lines = ""
        for oid, o in list(reversed(orders))[:5]:
            ico   = "✅" if o["status"] == "Completed" else "⏳"
            otype = "🔗" if o.get("order_type") == "redirect" else "🍪"
            recent_lines += f"{ico}{otype}  `{oid}`  —  {o['plan']}  —  {o['price']}\n"
        if not recent_lines:
            recent_lines = "📭 No orders yet — buy a plan to get started\\!"

        msg = (
            f"📊 *My Dashboard* 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  {user.first_name}\n"
            f"🆔  User ID:  `{user.id}`\n\n"
            f"📦  Total Orders:  {total}\n"
            f"✅  Completed:     {done}\n"
            f"⏳  Pending:       {total - done}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 *Recent Orders:*\n{recent_lines}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍪 Cookies",    callback_data="cookies_menu"),
             InlineKeyboardButton("🔗 Redirect",   callback_data="redirect_menu")],
            [InlineKeyboardButton("🎫 All Orders", callback_data="my_orders"),
             InlineKeyboardButton("💬 Support",    callback_data="support")],
            [InlineKeyboardButton("🔙 Menu",       callback_data="main_menu")],
        ])
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb)

    elif d == "my_orders":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]

        if not orders:
            body = "📭 No orders found\\.\n\nPurchase a plan to get started\\!"
        else:
            body = ""
            for oid, o in reversed(orders):
                ico   = "✅" if o["status"] == "Completed" else "⏳"
                otype = "🔗" if o.get("order_type") == "redirect" else "🍪"
                body += (
                    f"\n{ico}{otype} *{oid}*\n"
                    f"   Plan:   {o['plan']}\n"
                    f"   Price:  {o['price']}\n"
                    f"   Status: {o['status']}\n"
                )

        await q.edit_message_text(
            f"🎫 *My Orders*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{body}",
            parse_mode="MarkdownV2",
            reply_markup=kb_back(),
        )

    elif d == "support":
        msg = (
            f"💬 *Support Center* 💬\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕐 *24/7 Support Available*\n"
            f"⚡ Avg Response: \\< 15 minutes\n"
            f"🌟 Satisfaction Rate: 99\\.8\\%\n\n"
            f"📌 We handle:\n"
            f"  • Cookie delivery issues\n"
            f"  • Redirect link setup\n"
            f"  • Technical problems\n"
            f"  • Billing / payment queries\n"
            f"  • General questions\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Live chat: {SUPPORT_UN}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_support())

    elif d == "open_ticket":
        user = q.from_user
        msg = (
            f"🎟 *Support Ticket Created* 🎟\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Your ID:   `{user.id}`\n"
            f"👤  Username:  @{user.username or 'N/A'}\n\n"
            f"📌 *Next Steps:*\n"
            f"1️⃣  Message {SUPPORT_UN}\n"
            f"2️⃣  Include your ID: `{user.id}`\n"
            f"3️⃣  Describe your issue clearly\n\n"
            f"⚡ Response within *15 minutes*\\!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

    elif d == "faq":
        msg = (
            "📖 *FAQ — Frequently Asked Questions* 📖\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❓ *How fast is delivery?*\n"
            "✅  5–15 min after payment confirmation\n\n"
            "❓ *What cookie types do you offer?*\n"
            "✅  Yahoo, AOL, Office 365, Google Suite\n\n"
            "❓ *How long do cookies last?*\n"
            "✅  Plan‑dependent; built for max stability\n\n"
            "❓ *What is the Redirect Link service?*\n"
            "✅  Submit a URL → cloaked redirect link\n"
            "    or full PHP/HTML source code to self‑host\n\n"
            "❓ *Redirect pricing?*\n"
            "✅  Redirect Link: $100/mo  |  Source Code: $75/mo\n\n"
            "❓ *Accepted payment methods?*\n"
            "✅  BTC, USDT TRC20\n\n"
            "❓ *Do you refund?*\n"
            "✅  Yes — within 24 hrs if delivery fails\n\n"
            "❓ *What is Browser‑in‑Browser?*\n"
            "✅  Full browser session — no partial cookies\n\n"
            "❓ *Can I upgrade my plan?*\n"
            "✅  Yes — contact support anytime\n\n"
            "❓ *Is my data safe?*\n"
            "✅  100% encrypted delivery, zero logs\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_support())

    elif d == "about":
        await q.edit_message_text(
            ABOUT_MSG, parse_mode="MarkdownV2", reply_markup=kb_back()
        )


# ============================================================
#  ADMIN COMMANDS
# ============================================================

def _is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("❌ Unauthorized.")
        return
    total     = len(user_orders)
    pending   = sum(1 for o in user_orders.values() if o["status"] == "Pending")
    redirects = sum(1 for o in user_orders.values() if o.get("order_type") == "redirect")
    msg = (
        f"🔧 *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total Orders:  {total}\n"
        f"⏳ Pending:       {pending}\n"
        f"✅ Completed:     {total - pending}\n"
        f"🔗 Redirect Ords: {redirects}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Commands:*\n"
        f"`/complete <oid>`          — Mark complete & notify user\n"
        f"`/orders`                  — Last 20 orders\n"
        f"`/deliver <uid> <data>`    — Send cookie payload to user\n"
        f"`/deliver_rl <oid> <res>`  — Send redirect result to user\n"
        f"`/broadcast <msg>`         — Message all customers"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_complete(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /complete <order_id>")
        return
    oid = ctx.args[0].upper()
    if oid not in user_orders:
        await update.message.reply_text(f"❌ Order `{oid}` not found.", parse_mode="Markdown")
        return

    user_orders[oid]["status"] = "Completed"
    uid  = user_orders[oid]["user_id"]
    plan = user_orders[oid]["plan"]
    try:
        await ctx.bot.send_message(
            uid,
            f"✅ *Order Fulfilled\\!*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔  `{oid}`\n"
            f"📦  {plan}\n\n"
            f"Your order has been delivered to this chat\\.\n"
            f"Questions? /start → Support",
            parse_mode="MarkdownV2",
        )
    except Exception as exc:
        logger.warning("User notify failed: %s", exc)

    await update.message.reply_text(
        f"✅ `{oid}` marked complete & user notified.", parse_mode="Markdown"
    )


async def cmd_deliver(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Send cookie payload: /deliver <user_id> <cookie_data>"""
    if not _is_admin(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /deliver <user_id> <cookie_data>")
        return
    uid     = int(ctx.args[0])
    content = " ".join(ctx.args[1:])
    try:
        await ctx.bot.send_message(
            uid,
            f"📦 *Cookie Delivery*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"```\n{content}\n```\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"✅ Import into your browser\\.\n"
            f"Questions? /start → Support",
            parse_mode="MarkdownV2",
        )
        await update.message.reply_text(f"✅ Delivered to `{uid}`.", parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"❌ Failed: {exc}")


async def cmd_deliver_rl(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send redirect result to user: /deliver_rl <order_id> <link_or_source_code>
    For source code, paste the content (or use a multi-line message after the OID).
    """
    if not _is_admin(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /deliver_rl <order_id> <result>")
        return

    oid     = ctx.args[0].upper()
    content = " ".join(ctx.args[1:])

    if oid not in user_orders:
        await update.message.reply_text(f"❌ Order `{oid}` not found.", parse_mode="Markdown")
        return

    o       = user_orders[oid]
    uid     = o["user_id"]
    rl_type = o.get("rl_type", "link")
    rt      = REDIRECT_TYPES.get(rl_type, {"name": "Redirect Output", "emoji": "🔗"})

    try:
        await ctx.bot.send_message(
            uid,
            f"🔗 *Redirect Delivery* 🔗\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔  `{oid}`\n"
            f"{rt['emoji']}  Type: {rt['name']}\n\n"
            f"*Your Result:*\n"
            f"```\n{content}\n```\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"✅ Use or deploy as instructed\\.\n"
            f"Questions? /start → Support",
            parse_mode="MarkdownV2",
        )
        user_orders[oid]["status"] = "Completed"
        await update.message.reply_text(
            f"✅ Redirect result sent to `{uid}` for order `{oid}`.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        await update.message.reply_text(f"❌ Failed: {exc}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    if not user_orders:
        await update.message.reply_text("No orders yet.")
        return
    lines = "📋 *Last 20 Orders*\n━━━━━━━━━━━━━━━━━━\n"
    for oid, o in list(user_orders.items())[-20:][::-1]:
        ico   = "✅" if o["status"] == "Completed" else "⏳"
        otype = "🔗" if o.get("order_type") == "redirect" else "🍪"
        lines += f"{ico}{otype} `{oid}` | @{o['username']} | {o['plan']} | {o['price']}\n"
    await update.message.reply_text(lines, parse_mode="Markdown")


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    text    = " ".join(ctx.args)
    targets = set(o["user_id"] for o in user_orders.values())
    sent    = 0
    for uid in targets:
        try:
            await ctx.bot.send_message(
                uid, f"📢 *Announcement*\n\n{text}", parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent} user(s).")


# ============================================================
#  FALLBACK
# ============================================================

async def cmd_unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "❓ Unknown command — tap below to open the menu.",
        reply_markup=kb_main(),
    )


# ============================================================
#  APPLICATION FACTORY
# ============================================================

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # ── User commands ──
    app.add_handler(CommandHandler("start",       cmd_start))

    # ── Admin commands ──
    app.add_handler(CommandHandler("admin",       cmd_admin))
    app.add_handler(CommandHandler("complete",    cmd_complete))
    app.add_handler(CommandHandler("deliver",     cmd_deliver))
    app.add_handler(CommandHandler("deliver_rl",  cmd_deliver_rl))
    app.add_handler(CommandHandler("orders",      cmd_orders))
    app.add_handler(CommandHandler("broadcast",   cmd_broadcast))

    # ── Inline callbacks ──
    app.add_handler(CallbackQueryHandler(callback_router))

    # ── Free-text handler (redirect URL input) ──
    # Must be registered BEFORE the unknown-command catch-all
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ── Catch-all unknown commands ──
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    return app


# ============================================================
#  ENTRY POINT — Webhook mode for Render
# ============================================================

def main() -> None:
    logger.info("🍪 Starting Red Eye Cookies Bot v2 [webhook mode]")
    logger.info("PORT=%s  WEBHOOK_URL=%s", PORT, WEBHOOK_URL)

    app = build_app()
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{WEBHOOK_PATH}",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
