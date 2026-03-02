#!/usr/bin/env python3
"""
Red Eye Cookies Bot — v2
Cookies | Redirect Links | Full Session Access
Optimized for Render.com deployment using Webhooks
"""
import asyncio
import sys
import random
import string

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
#  IN-MEMORY STORES
# ============================================================
user_orders: dict  = {}
order_counter: list = [0]
user_states: dict  = {}   # { user_id: {"state": str, "data": dict} }


def next_order_id(user_id: int) -> str:
    order_counter[0] += 1
    return f"ORD-{user_id}-{order_counter[0]:05d}"


def rand_token(n: int = 14) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


# ============================================================
#  SUBSCRIPTION PLANS
# ============================================================
PLANS = {
    "wk_basic": {
        "name": "Weekly Basic", "tier": "WEEKLY",
        "duration": "7 Days", "price": "$9.99", "emoji": "🟢",
        "features": [
            "1 Active Account", "Browser‑in‑Browser Support",
            "Email Access Included", "Background Logo Grab", "Basic 24/7 Support",
        ],
    },
    "wk_pro": {
        "name": "Weekly Pro", "tier": "WEEKLY",
        "duration": "7 Days", "price": "$14.99", "emoji": "🔵",
        "features": [
            "3 Active Accounts", "Browser‑in‑Browser Support",
            "Email + Background Logo", "Long‑Lasting Cookie Stability", "Priority 24/7 Support",
        ],
    },
    "bw_basic": {
        "name": "Bi‑Weekly Basic", "tier": "BI‑WEEKLY",
        "duration": "14 Days", "price": "$17.99", "emoji": "🟡",
        "features": [
            "1 Active Account", "Browser‑in‑Browser Support",
            "Email Access Included", "Background Logo Grab", "Basic 24/7 Support",
        ],
    },
    "bw_pro": {
        "name": "Bi‑Weekly Pro", "tier": "BI‑WEEKLY",
        "duration": "14 Days", "price": "$24.99", "emoji": "🟠",
        "features": [
            "5 Active Accounts", "Browser‑in‑Browser Support",
            "Email + Background Logo", "Long‑Lasting Cookie Stability", "Priority 24/7 Support",
        ],
    },
    "mo_basic": {
        "name": "Monthly Basic", "tier": "MONTHLY",
        "duration": "30 Days", "price": "$29.99", "emoji": "🔴",
        "features": [
            "1 Active Account", "Browser‑in‑Browser Support",
            "Email Access Included", "Background Logo Grab", "Basic 24/7 Support",
        ],
    },
    "mo_pro": {
        "name": "Monthly Pro", "tier": "MONTHLY",
        "duration": "30 Days", "price": "$44.99", "emoji": "⚡",
        "features": [
            "10 Active Accounts", "Browser‑in‑Browser Support",
            "Email + Background Logo", "Long‑Lasting Cookie Stability", "Priority 24/7 Support",
        ],
    },
    "mo_elite": {
        "name": "Monthly Elite", "tier": "MONTHLY",
        "duration": "30 Days", "price": "$69.99", "emoji": "👑",
        "features": [
            "Unlimited Accounts", "Browser‑in‑Browser Support",
            "Email + Background Logo", "Maximum Cookie Stability",
            "VIP 24/7 Support", "Instant Telegram Delivery",
        ],
    },
}

# ============================================================
#  COOKIE TYPE PLANS  (Yahoo / AOL / Office 365 / GSuite)
# ============================================================
COOKIE_TYPES = {
    "ck_yahoo": {
        "name": "Yahoo Cookies", "platform": "Yahoo",
        "price": "$19.99", "emoji": "🟣",
        "features": [
            "Fresh Yahoo Session Cookies",
            "Email Access Included",
            "Browser‑in‑Browser Support",
            "Background Logo Grab",
            "Long‑Lasting Stability",
            "Instant Telegram Delivery",
            "24/7 Support",
        ],
    },
    "ck_aol": {
        "name": "AOL Cookies", "platform": "AOL",
        "price": "$19.99", "emoji": "🔷",
        "features": [
            "Fresh AOL Session Cookies",
            "Email Access Included",
            "Browser‑in‑Browser Support",
            "Background Logo Grab",
            "Long‑Lasting Stability",
            "Instant Telegram Delivery",
            "24/7 Support",
        ],
    },
    "ck_office": {
        "name": "Office 365 Cookies", "platform": "Microsoft Office 365",
        "price": "$29.99", "emoji": "🏢",
        "features": [
            "Fresh Office 365 Session Cookies",
            "Full Suite Access Included",
            "Browser‑in‑Browser Support",
            "Background Logo Grab",
            "Long‑Lasting Stability",
            "Instant Telegram Delivery",
            "Priority 24/7 Support",
        ],
    },
    "ck_gsuite": {
        "name": "GSuite Cookies", "platform": "Google Workspace",
        "price": "$29.99", "emoji": "🌐",
        "features": [
            "Fresh Google Workspace Cookies",
            "Full G‑Suite Access Included",
            "Browser‑in‑Browser Support",
            "Background Logo Grab",
            "Long‑Lasting Stability",
            "Instant Telegram Delivery",
            "Priority 24/7 Support",
        ],
    },
}

# ============================================================
#  REDIRECT LINK PLANS
# ============================================================
REDIRECT_PLANS = {
    "rd_link": {
        "name": "Redirect Link",
        "price": "$100", "billing": "Monthly",
        "emoji": "🔗", "output_type": "link",
        "features": [
            "Custom Redirect URL Generated",
            "Unique Obfuscated Short Link",
            "Unlimited Redirects Per Month",
            "Fast CDN‑Backed Delivery",
            "Anti‑Bot Detection Bypass",
            "Click Analytics Included",
            "24/7 Priority Support",
        ],
    },
    "rd_source": {
        "name": "Redirect Source Code",
        "price": "$75", "billing": "Monthly",
        "emoji": "💻", "output_type": "source",
        "features": [
            "Full HTML/JS Source Code Provided",
            "Self‑Hosted — You Own It Fully",
            "Meta‑Refresh + JS Dual Redirect",
            "Anti‑Bot Bypass Layer Built‑In",
            "Customizable Branding & Delay",
            "One‑Click Deploy Instructions",
            "24/7 Priority Support",
        ],
    },
}


# ============================================================
#  PROTOTYPE OUTPUT GENERATORS
# ============================================================

def proto_redirect_link(target_url: str) -> str:
    token = rand_token(14)
    return f"https://rd.redeye.io/r/{token}"


def proto_redirect_source(target_url: str) -> str:
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        f'  <meta http-equiv="refresh" content="0; url={target_url}">',
        "  <title>Loading...</title>",
        "  <script>",
        "    (function() {",
        "      // Red Eye Anti-Bot Bypass v2",
        f"      var u = '{target_url}';",
        "      if (window.self === window.top) {",
        "        setTimeout(function(){ window.location.replace(u); }, 80);",
        "      }",
        "    })();",
        "  </script>",
        "  <style>",
        "    *{margin:0;padding:0;box-sizing:border-box}",
        "    body{background:#080808;color:#fff;display:flex;",
        "         justify-content:center;align-items:center;",
        "         height:100vh;font-family:Arial,sans-serif}",
        "  </style>",
        "</head>",
        "<body><p>&#9203; Redirecting&hellip;</p></body>",
        "</html>",
    ]
    return "\n".join(lines)


# ============================================================
#  KEYBOARD BUILDERS
# ============================================================

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  Buy Cookies",   callback_data="buy_now"),
         InlineKeyboardButton("📋  All Plans",     callback_data="plans")],
        [InlineKeyboardButton("🍪  Cookie Types",  callback_data="cookie_types"),
         InlineKeyboardButton("🔗  Redirect Link", callback_data="redirect_menu")],
        [InlineKeyboardButton("📊  My Dashboard",  callback_data="dashboard"),
         InlineKeyboardButton("🎫  My Orders",     callback_data="my_orders")],
        [InlineKeyboardButton("💬  Support",       callback_data="support"),
         InlineKeyboardButton("ℹ️  About",         callback_data="about")],
        [InlineKeyboardButton("📢  Our Channel",   url=CHANNEL_URL)],
    ])


def kb_plans() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  WEEKLY PLANS  ━━━",  callback_data="noop")],
        [InlineKeyboardButton("🟢 Basic  $9.99",  callback_data="plan_wk_basic"),
         InlineKeyboardButton("🔵 Pro  $14.99",   callback_data="plan_wk_pro")],
        [InlineKeyboardButton("━━  BI‑WEEKLY PLANS  ━━", callback_data="noop")],
        [InlineKeyboardButton("🟡 Basic  $17.99", callback_data="plan_bw_basic"),
         InlineKeyboardButton("🟠 Pro  $24.99",   callback_data="plan_bw_pro")],
        [InlineKeyboardButton("━━━  MONTHLY PLANS  ━━━", callback_data="noop")],
        [InlineKeyboardButton("🔴 Basic  $29.99", callback_data="plan_mo_basic"),
         InlineKeyboardButton("⚡ Pro  $44.99",   callback_data="plan_mo_pro")],
        [InlineKeyboardButton("👑  Elite  $69.99  — BEST VALUE", callback_data="plan_mo_elite")],
        [InlineKeyboardButton("🔙 Back",          callback_data="main_menu")],
    ])


def kb_plan_detail(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase This Plan", callback_data=f"buy_{plan_key}")],
        [InlineKeyboardButton("📋  All Plans", callback_data="plans"),
         InlineKeyboardButton("🔙  Menu",      callback_data="main_menu")],
    ])


def kb_payment(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"pay_btc_{plan_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"pay_usdt_{plan_key}")],
        [InlineKeyboardButton("🔙  Back to Plans",       callback_data="plans")],
    ])


def kb_cookie_types() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  EMAIL COOKIES  ━━━", callback_data="noop")],
        [InlineKeyboardButton("🟣  Yahoo   $19.99", callback_data="ck_yahoo"),
         InlineKeyboardButton("🔷  AOL     $19.99", callback_data="ck_aol")],
        [InlineKeyboardButton("━━  BUSINESS COOKIES  ━━", callback_data="noop")],
        [InlineKeyboardButton("🏢  Office 365  $29.99", callback_data="ck_office"),
         InlineKeyboardButton("🌐  GSuite      $29.99", callback_data="ck_gsuite")],
        [InlineKeyboardButton("🔙  Back", callback_data="main_menu")],
    ])


def kb_cookie_detail(ck_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase Now",   callback_data=f"buy_ck_{ck_key}")],
        [InlineKeyboardButton("🍪  All Types", callback_data="cookie_types"),
         InlineKeyboardButton("🔙  Menu",      callback_data="main_menu")],
    ])


def kb_ck_payment(ck_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"ckpay_btc_{ck_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"ckpay_usdt_{ck_key}")],
        [InlineKeyboardButton("🔙  Back",               callback_data="cookie_types")],
    ])


def kb_redirect_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗  Redirect Link   — $100/mo", callback_data="rdplan_rd_link")],
        [InlineKeyboardButton("💻  Source Code     — $75/mo",  callback_data="rdplan_rd_source")],
        [InlineKeyboardButton("🔙  Back",                      callback_data="main_menu")],
    ])


def kb_redirect_detail(rd_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀  Preview (Enter Your URL)", callback_data=f"rd_preview_{rd_key}")],
        [InlineKeyboardButton("✅  Purchase Now",             callback_data=f"buy_rd_{rd_key}")],
        [InlineKeyboardButton("🔙  Back",                    callback_data="redirect_menu")],
    ])


def kb_after_preview(rd_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase Full Version", callback_data=f"buy_rd_{rd_key}")],
        [InlineKeyboardButton("🔄  Try Another URL",       callback_data=f"rd_preview_{rd_key}")],
        [InlineKeyboardButton("🔙  Main Menu",             callback_data="main_menu")],
    ])


def kb_redirect_payment(rd_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"rdpay_btc_{rd_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"rdpay_usdt_{rd_key}")],
        [InlineKeyboardButton("🔙  Back",               callback_data="redirect_menu")],
    ])


def kb_cancel_input() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌  Cancel", callback_data="main_menu")],
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
🍪 *Welcome to Red Eye Cookies Bot\\!* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 *Your \\#1 Source for Premium Sessions & Tools*

🍪 *Fresh Cookies — Now Available:*
  ✅  Yahoo  \\|  AOL  \\|  Office 365  \\|  GSuite
  ✅  All Platforms In Stock — Tested Daily
  ✅  Browser‑in‑Browser & Full Email Access

🔗 *NEW\\!  Redirect Link Service:*
  ✅  Custom Redirect URL — $100/mo
  ✅  Full HTML Source Code — $75/mo
  ✅  Anti‑Bot Bypass Built‑In
  ✅  Try a Free Prototype Preview Before You Buy

⚡ *Every Plan Also Includes:*
  ✅  Background Logo Grab
  ✅  Long‑Lasting Cookie Stability
  ✅  Instant Telegram Delivery
  ✅  24/7 Support Team Ready to Help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦  *7 Subscription Plans  \\|  4 Cookie Types*
🟢 Weekly  \\|  🟡 Bi‑Weekly  \\|  👑 Monthly

👇 *Select an option below to get started\\!*\
"""

ABOUT_MSG = """\
🍪 *About Red Eye Cookies* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 *Why Choose Us?*

🔐 *Fast & Secure* — Instant delivery, zero logs
🌐 *Browser‑in‑Browser* — Full session compatibility
🍪 *4 Cookie Types* — Yahoo \\| AOL \\| Office 365 \\| GSuite
🔗 *Redirect Links* — Custom URLs & source code service
📦 *7 Flexible Plans* — Weekly, Bi‑Weekly & Monthly
🎨 *Logo & Email Grab* — Authentic session data included
⏳ *Long‑Lasting Cookies* — Maximum stability built‑in
🛡️ *24/7 Support* — Always here when you need us
📲 *User Dashboard* — Manage all orders in one place
📩 *Direct Telegram Delivery* — No external links needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Questions? Hit Support below\\!\
"""


# ============================================================
#  /start
# ============================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_states.pop(user.id, None)
    logger.info("CMD /start — uid=%s @%s", user.id, user.username)
    await update.message.reply_text(
        WELCOME,
        parse_mode="MarkdownV2",
        reply_markup=kb_main(),
    )


# ============================================================
#  TEXT MESSAGE HANDLER  (URL input for Redirect Preview)
# ============================================================

async def handle_text_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user       = update.effective_user
    state_info = user_states.get(user.id)

    if not state_info or state_info.get("state") != "awaiting_rd_url":
        await update.message.reply_text(
            "👇 Use the menu below to navigate:",
            reply_markup=kb_main(),
        )
        return

    url    = update.message.text.strip()
    rd_key = state_info["data"]["rd_key"]

    # Basic validation — keep state so user can retry
    if len(url) < 5 or ("." not in url and "/" not in url):
        await update.message.reply_text(
            "⚠️ That doesn't look like a valid URL.\n\n"
            "Please enter a full URL, e.g. `https://example.com`",
            parse_mode="Markdown",
            reply_markup=kb_cancel_input(),
        )
        return

    # Normalise scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    rp = REDIRECT_PLANS.get(rd_key)
    if not rp:
        user_states.pop(user.id, None)
        return

    # Clear state
    user_states.pop(user.id, None)

    if rp["output_type"] == "link":
        proto_out = proto_redirect_link(url)
        msg = (
            f"🔗 *Redirect Link — Prototype Preview*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 *Target URL:*\n`{url}`\n\n"
            f"🚀 *Prototype Redirect Link:*\n`{proto_out}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Prototype only* — link is not live.\n"
            f"Purchase the full version to activate:\n"
            f"  ✅ CDN‑backed delivery\n"
            f"  ✅ Click analytics dashboard\n"
            f"  ✅ Anti‑bot bypass enabled\n\n"
            f"💰 *Full Version: $100/mo*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        source = proto_redirect_source(url)
        msg = (
            f"💻 *Source Code — Prototype Preview*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 *Target URL:*\n`{url}`\n\n"
            f"🚀 *Prototype Source Code:*\n"
            f"```html\n{source}\n```\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Prototype only* — for demo purposes.\n"
            f"Purchase the full version to receive:\n"
            f"  ✅ Production‑ready anti‑bot code\n"
            f"  ✅ Custom branding & delay control\n"
            f"  ✅ One‑click deploy instructions\n\n"
            f"💰 *Full Version: $75/mo*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=kb_after_preview(rd_key),
    )


# ============================================================
#  CALLBACK ROUTER
# ============================================================

async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    d   = q.data
    uid = q.from_user.id

    # Clear any pending URL‑input state whenever the user taps a button
    # (rd_preview_ branch will re‑set it right after)
    if not d.startswith("rd_preview_"):
        user_states.pop(uid, None)

    # ── NOOP (section headers) ──────────────────────────────
    if d == "noop":
        return

    # ── MAIN MENU ───────────────────────────────────────────
    elif d == "main_menu":
        await q.edit_message_text(
            WELCOME, parse_mode="MarkdownV2", reply_markup=kb_main()
        )

    # ── BUY NOW / PLANS ─────────────────────────────────────
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
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_plans())

    # ── COOKIE TYPES MENU ───────────────────────────────────
    elif d == "cookie_types":
        msg = (
            "🍪 *Cookie Types*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select your platform below.\n"
            "All cookies are freshly sourced, browser‑in‑browser compatible,\n"
            "and delivered instantly to Telegram.\n\n"
            "🟣 *Yahoo* & 🔷 *AOL* — Email Sessions — `$19.99`\n"
            "🏢 *Office 365* & 🌐 *GSuite* — Business Sessions — `$29.99`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_cookie_types())

    # ── COOKIE TYPE DETAIL ──────────────────────────────────
    elif d in ("ck_yahoo", "ck_aol", "ck_office", "ck_gsuite"):
        ck = COOKIE_TYPES.get(d)
        if not ck:
            return
        feats = "\n".join(f"   ✅ {f}" for f in ck["features"])
        msg = (
            f"{ck['emoji']} *{ck['name']}* {ck['emoji']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐  *Platform:* {ck['platform']}\n"
            f"💵  *Price:*    {ck['price']}\n\n"
            f"🗂 *What's Included:*\n{feats}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Delivery: Instant to Telegram\n"
            f"🔐 Fully Encrypted Transfer\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_cookie_detail(d))

    # ── COOKIE CHECKOUT  (must precede generic buy_) ────────
    elif d.startswith("buy_ck_"):
        ck_key = d[7:]          # e.g. "ck_yahoo"
        ck     = COOKIE_TYPES.get(ck_key)
        if not ck:
            return
        msg = (
            f"💳 *Checkout — {ck['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 Platform: {ck['platform']}\n"
            f"💵 Amount:   *{ck['price']}*\n\n"
            f"Select your payment method below 👇\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_ck_payment(ck_key))

    # ── COOKIE PAYMENT ──────────────────────────────────────
    elif d.startswith("ckpay_btc_") or d.startswith("ckpay_usdt_"):
        if d.startswith("ckpay_btc_"):
            method, ck_key, addr = "BTC", d[10:], CRYPTO_ADDR
        else:
            method, ck_key, addr = "USDT (TRC20)", d[11:], USDT_ADDR

        ck = COOKIE_TYPES.get(ck_key)
        if not ck:
            return

        user = q.from_user
        oid  = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":  user.id,
            "username": user.username or "N/A",
            "plan_key": ck_key,
            "plan":     ck["name"],
            "price":    ck["price"],
            "method":   method,
            "status":   "Pending",
            "type":     "cookie",
        }

        msg = (
            f"📝 *Order Created Successfully\\!* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Order ID:  `{oid}`\n"
            f"🍪  Product:   {ck['name']}\n"
            f"💵  Amount:    {ck['price']}\n"
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
                f"🔔 *NEW COOKIE ORDER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username}  \\(`{user.id}`\\)\n"
                f"🍪  {ck['name']}\n"
                f"💵  {ck['price']}\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Use `/complete {oid}` when confirmed\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ── REDIRECT MENU ────────────────────────────────────────
    elif d == "redirect_menu":
        msg = (
            "🔗 *Redirect Link Service*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Enter any target URL and we generate a custom redirect for you.\n\n"
            "📦 *Choose your output type:*\n\n"
            "🔗 *Redirect Link — $100/mo*\n"
            "   A unique obfuscated short URL that redirects visitors\n"
            "   to your target. Includes CDN delivery, analytics &\n"
            "   anti‑bot bypass.\n\n"
            "💻 *Source Code — $75/mo*\n"
            "   Full HTML/JS you self‑host. Includes dual redirect,\n"
            "   anti‑bot layer & one‑click deploy instructions.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 *Try a FREE prototype preview before you buy!*"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_redirect_menu())

    # ── REDIRECT PLAN DETAIL ─────────────────────────────────
    elif d.startswith("rdplan_"):
        rd_key = d[7:]          # "rd_link" or "rd_source"
        rp     = REDIRECT_PLANS.get(rd_key)
        if not rp:
            return
        feats = "\n".join(f"   ✅ {f}" for f in rp["features"])
        msg = (
            f"{rp['emoji']} *{rp['name']}* {rp['emoji']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💵  *Price:*   {rp['price']}/mo\n"
            f"🗓  *Billing:* {rp['billing']}\n\n"
            f"🗂 *What's Included:*\n{feats}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Try a prototype preview — enter any URL to see a sample output!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_redirect_detail(rd_key)
        )

    # ── REDIRECT PREVIEW  (prompt user for URL) ──────────────
    elif d.startswith("rd_preview_"):
        rd_key = d[11:]         # "rd_link" or "rd_source"
        rp     = REDIRECT_PLANS.get(rd_key)
        if not rp:
            return

        # Set awaiting state
        user_states[uid] = {"state": "awaiting_rd_url", "data": {"rd_key": rd_key}}

        label = "redirect link" if rp["output_type"] == "link" else "source code"
        msg = (
            f"🔗 *Enter Your Target URL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 Selected: *{rp['name']}* ({rp['price']}/mo)\n\n"
            f"Type or paste the URL you want to generate a {label} for:\n\n"
            f"Example: `https://yoursite.com`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ A prototype will be generated instantly!\n"
            f"Tap ❌ Cancel below to go back."
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_cancel_input())

    # ── REDIRECT CHECKOUT  (must precede generic buy_) ───────
    elif d.startswith("buy_rd_"):
        rd_key = d[7:]          # "rd_link" or "rd_source"
        rp     = REDIRECT_PLANS.get(rd_key)
        if not rp:
            return
        msg = (
            f"💳 *Checkout — {rp['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Product:  {rp['name']}\n"
            f"🗓  Billing:  {rp['billing']}\n"
            f"💵 Amount:   *{rp['price']}/mo*\n\n"
            f"Select your payment method below 👇\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=kb_redirect_payment(rd_key)
        )

    # ── REDIRECT PAYMENT ─────────────────────────────────────
    elif d.startswith("rdpay_btc_") or d.startswith("rdpay_usdt_"):
        if d.startswith("rdpay_btc_"):
            method, rd_key, addr = "BTC", d[10:], CRYPTO_ADDR
        else:
            method, rd_key, addr = "USDT (TRC20)", d[11:], USDT_ADDR

        rp = REDIRECT_PLANS.get(rd_key)
        if not rp:
            return

        user = q.from_user
        oid  = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":  user.id,
            "username": user.username or "N/A",
            "plan_key": rd_key,
            "plan":     rp["name"],
            "price":    f"{rp['price']}/mo",
            "method":   method,
            "status":   "Pending",
            "type":     "redirect",
        }

        msg = (
            f"📝 *Order Created Successfully\\!* 📝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔  Order ID:  `{oid}`\n"
            f"🔗  Product:   {rp['name']}\n"
            f"💵  Amount:    {rp['price']}/mo\n"
            f"💳  Method:    {method}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📬 *Send Exact Amount To:*\n"
            f"`{addr}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *After Payment — 3 Steps:*\n"
            f"1️⃣  Screenshot or copy TX hash\n"
            f"2️⃣  Message {SUPPORT_UN} with Order ID\n"
            f"3️⃣  Service activated within *1 hour* ✅\n\n"
            f"⚠️  Order expires in *30 minutes*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_back())

        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🔔 *NEW REDIRECT ORDER*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username}  \\(`{user.id}`\\)\n"
                f"🔗  {rp['name']}\n"
                f"💵  {rp['price']}/mo\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Use `/complete {oid}` when confirmed\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ── PLAN DETAIL ─────────────────────────────────────────
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
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_plan_detail(key))

    # ── CHECKOUT (subscription plans) ───────────────────────
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
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_payment(key))

    # ── PAYMENT (subscription plans) ────────────────────────
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
            "user_id":  user.id,
            "username": user.username or "N/A",
            "plan_key": key,
            "plan":     p["name"],
            "price":    p["price"],
            "method":   method,
            "status":   "Pending",
            "type":     "subscription",
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
                f"👤  @{user.username}  \\(`{user.id}`\\)\n"
                f"📦  {p['name']}\n"
                f"💵  {p['price']}\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━\n"
                f"✅ Use `/complete {oid}` when confirmed\\.",
                parse_mode="MarkdownV2",
            )
        except Exception as exc:
            logger.warning("Admin notify failed: %s", exc)

    # ── DASHBOARD ───────────────────────────────────────────
    elif d == "dashboard":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]
        total  = len(orders)
        done   = sum(1 for _, o in orders if o["status"] == "Completed")

        recent_lines = ""
        for oid, o in list(reversed(orders))[:5]:
            ico = "✅" if o["status"] == "Completed" else "⏳"
            recent_lines += f"{ico}  `{oid}`  —  {o['plan']}  —  {o['price']}\n"
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
            [InlineKeyboardButton("🛒 New Order",  callback_data="plans"),
             InlineKeyboardButton("🎫 All Orders", callback_data="my_orders")],
            [InlineKeyboardButton("💬 Support",    callback_data="support"),
             InlineKeyboardButton("🔙 Menu",       callback_data="main_menu")],
        ])
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb)

    # ── ALL ORDERS ──────────────────────────────────────────
    elif d == "my_orders":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]

        if not orders:
            body = "📭 No orders found\\.\n\nPurchase a plan to get started\\!"
        else:
            body = ""
            for oid, o in reversed(orders):
                ico  = "✅" if o["status"] == "Completed" else "⏳"
                body += (
                    f"\n{ico} *{oid}*\n"
                    f"   Plan:   {o['plan']}\n"
                    f"   Price:  {o['price']}\n"
                    f"   Status: {o['status']}\n"
                )

        await q.edit_message_text(
            f"🎫 *My Orders*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{body}",
            parse_mode="MarkdownV2",
            reply_markup=kb_back(),
        )

    # ── SUPPORT ─────────────────────────────────────────────
    elif d == "support":
        msg = (
            f"💬 *Support Center* 💬\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕐 *24/7 Support Available*\n"
            f"⚡ Avg Response: \\< 15 minutes\n"
            f"🌟 Satisfaction Rate: 99\\.8\\%\n\n"
            f"📌 We handle:\n"
            f"  • Cookie delivery issues\n"
            f"  • Redirect link activation\n"
            f"  • Technical problems\n"
            f"  • Billing / payment queries\n"
            f"  • General questions\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Live chat: {SUPPORT_UN}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await q.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=kb_support())

    # ── OPEN TICKET ─────────────────────────────────────────
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

    # ── FAQ ─────────────────────────────────────────────────
    elif d == "faq":
        msg = (
            "📖 *FAQ — Frequently Asked Questions* 📖\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❓ *Which cookie platforms do you support?*\n"
            "✅  Yahoo, AOL, Office 365, GSuite & more\n\n"
            "❓ *How fast is cookie delivery?*\n"
            "✅  5–15 min after payment confirmation\n\n"
            "❓ *How long do cookies last?*\n"
            "✅  Plan‑dependent; built for max stability\n\n"
            "❓ *What is the Redirect Link service?*\n"
            "✅  We generate a custom redirect URL or full\n"
            "    HTML/JS source code for any target URL\n\n"
            "❓ *Redirect Link vs Source Code?*\n"
            "✅  Link ($100/mo) — hosted short URL we manage\n"
            "✅  Source ($75/mo) — full code you self‑host\n\n"
            "❓ *Can I preview before buying?*\n"
            "✅  Yes! Use the free prototype preview feature\n\n"
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

    # ── ABOUT ───────────────────────────────────────────────
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
    total   = len(user_orders)
    pending = sum(1 for o in user_orders.values() if o["status"] == "Pending")
    subs    = sum(1 for o in user_orders.values() if o.get("type") == "subscription")
    cookies = sum(1 for o in user_orders.values() if o.get("type") == "cookie")
    redir   = sum(1 for o in user_orders.values() if o.get("type") == "redirect")
    msg = (
        f"🔧 *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total:       {total}\n"
        f"⏳ Pending:     {pending}\n"
        f"✅ Completed:   {total - pending}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🍪 Cookie:      {cookies}\n"
        f"📋 Sub Plans:   {subs}\n"
        f"🔗 Redirect:    {redir}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Commands:\n"
        f"`/complete <order_id>` — Mark complete \\& notify\n"
        f"`/orders`              — Last 20 orders\n"
        f"`/deliver <uid> <data>`— Push payload to user\n"
        f"`/broadcast <msg>`     — Message all customers"
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
            f"🍪 *Order Fulfilled\\!*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔  `{oid}`\n"
            f"📦  {plan}\n\n"
            f"Your order has been delivered to this chat\\.\n"
            f"If you need help: /start → Support",
            parse_mode="MarkdownV2",
        )
    except Exception as exc:
        logger.warning("User notify failed: %s", exc)

    await update.message.reply_text(
        f"✅ `{oid}` marked complete & user notified.", parse_mode="Markdown"
    )


async def cmd_deliver(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Push payload to user: /deliver <user_id> <data>"""
    if not _is_admin(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /deliver <user_id> <data>")
        return
    uid     = int(ctx.args[0])
    content = " ".join(ctx.args[1:])
    try:
        await ctx.bot.send_message(
            uid,
            f"📦 *Delivery*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"```\n{content}\n```\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"✅ Import/use as instructed\\.\n"
            f"Questions? /start → Support",
            parse_mode="MarkdownV2",
        )
        await update.message.reply_text(f"✅ Delivered to `{uid}`.", parse_mode="Markdown")
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
        kind  = o.get("type", "sub")[0].upper()
        lines += f"{ico} [{kind}] `{oid}` | @{o['username']} | {o['plan']} | {o['price']}\n"
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
            await ctx.bot.send_message(uid, f"📢 *Announcement*\n\n{text}", parse_mode="Markdown")
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

    # ── User commands ────────────────────────────────────────
    app.add_handler(CommandHandler("start",     cmd_start))

    # ── Admin commands ───────────────────────────────────────
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("complete",  cmd_complete))
    app.add_handler(CommandHandler("deliver",   cmd_deliver))
    app.add_handler(CommandHandler("orders",    cmd_orders))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # ── Inline button callbacks ──────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_router))

    # ── Text messages (URL input for redirect preview) ───────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # ── Unknown commands catch-all ───────────────────────────
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
