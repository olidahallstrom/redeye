#!/usr/bin/env python3
"""
Red Eye Cookies Bot
Optimized for Render.com deployment using Webhooks
"""
import asyncio
import sys

# Fix for Python 3.10+ asyncio behavior
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
#  LOGGING — Render captures stdout automatically
# ============================================================
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
#  CONFIG — Loaded from Render Environment Variables
# ============================================================
BOT_TOKEN   = os.environ["BOT_TOKEN"]               # Required
WEBHOOK_URL = os.environ["WEBHOOK_URL"]             # e.g. https://your-app.onrender.com
ADMIN_ID    = int(os.environ["ADMIN_ID"])           # Required
PORT        = int(os.environ.get("PORT", 8080))     # Render injects PORT automatically
SUPPORT_UN  = os.environ.get("SUPPORT_UN",  "@support")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/channel")
CRYPTO_ADDR = os.environ.get("CRYPTO_ADDR", "SET_YOUR_BTC_ADDRESS")
USDT_ADDR   = os.environ.get("USDT_ADDR",   "SET_YOUR_USDT_ADDRESS")

# Webhook path = token (security best practice — random-looking URL)
WEBHOOK_PATH = BOT_TOKEN

# ============================================================
#  IN-MEMORY ORDER STORE
#  For production swap this with PostgreSQL (Render add-on)
# ============================================================
user_orders: dict   = {}
order_counter: list = [0]


def next_order_id(user_id: int) -> str:
    order_counter[0] += 1
    return f"ORD-{user_id}-{order_counter[0]:05d}"


# ============================================================
#  PLANS
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
        "name": "Weekly Pro",  "tier": "WEEKLY",
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
        [InlineKeyboardButton("🛒  Buy Now",         callback_data="buy_now"),
         InlineKeyboardButton("📋  Plans & Pricing", callback_data="plans")],
        [InlineKeyboardButton("📊  My Dashboard",    callback_data="dashboard"),
         InlineKeyboardButton("🎫  My Orders",       callback_data="my_orders")],
        [InlineKeyboardButton("💬  Support",         callback_data="support"),
         InlineKeyboardButton("ℹ️  About",           callback_data="about")],
        [InlineKeyboardButton("📢  Our Channel",     url=CHANNEL_URL)],
    ])


def kb_plans() -> InlineKeyboardMarkup:
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


def kb_payment(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",        callback_data=f"pay_btc_{plan_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"pay_usdt_{plan_key}")],
        [InlineKeyboardButton("🔙  Back to Plans",       callback_data="plans")],
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

🔥 *Your \\#1 Source for Premium Cookies*

✅  All Types of Links In Stock
✅  Fast & Secure Delivery
✅  Browser‑in‑Browser Support
✅  Background Logo & Email Included
✅  Long‑Lasting Cookies for Stability
✅  Results Delivered Directly to Telegram
✅  24/7 Support Team Ready to Assist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦  *7 Flexible Plans Available*
🟢 Weekly  \\|  🟡 Bi‑Weekly  \\|  👑 Monthly

👇 *Select an option below to get started\\!*\
"""

ABOUT_MSG = """\
🍪 *About Red Eye Cookies* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 *Why Choose Us?*

🔐 *Fast & Secure* — Instant delivery to your inbox
🌐 *Browser‑in‑Browser* — Full session compatibility
📦 *7 Flexible Plans* — Weekly, Bi‑Weekly & Monthly
🎨 *Logo & Email Grab* — Authentic session data
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
    logger.info("CMD /start — uid=%s @%s", user.id, user.username)
    await update.message.reply_text(
        WELCOME,
        parse_mode="MarkdownV2",
        reply_markup=kb_main(),
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

    # ── CHECKOUT ────────────────────────────────────────────
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

    # ── PAYMENT ─────────────────────────────────────────────
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

        # Notify admin
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
                ico   = "✅" if o["status"] == "Completed" else "⏳"
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
            f"  • Delivery issues\n"
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
            "❓ *How fast is delivery?*\n"
            "✅  5–15 min after payment confirmation\n\n"
            "❓ *How long do cookies last?*\n"
            "✅  Plan‑dependent; built for max stability\n\n"
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
    msg = (
        f"🔧 *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total:     {total}\n"
        f"⏳ Pending:   {pending}\n"
        f"✅ Completed: {total - pending}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Commands:\n"
        f"`/complete <order_id>` — Mark complete \\& notify user\n"
        f"`/orders`              — Last 20 orders\n"
        f"`/deliver <uid> <data>`— Send cookies to user\n"
        f"`/broadcast <msg>`    — Message all customers"
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
            f"Your cookies have been delivered to this chat\\.\n"
            f"If you need help: /start → Support",
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


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    if not user_orders:
        await update.message.reply_text("No orders yet.")
        return
    lines = "📋 *Last 20 Orders*\n━━━━━━━━━━━━━━━━━━\n"
    for oid, o in list(user_orders.items())[-20:][::-1]:
        ico    = "✅" if o["status"] == "Completed" else "⏳"
        lines += f"{ico} `{oid}` | @{o['username']} | {o['plan']} | {o['price']}\n"
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

    # User
    app.add_handler(CommandHandler("start",     cmd_start))

    # Admin
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("complete",  cmd_complete))
    app.add_handler(CommandHandler("deliver",   cmd_deliver))
    app.add_handler(CommandHandler("orders",    cmd_orders))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    # Catch-all
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    return app


# ============================================================
#  ENTRY POINT — Webhook mode for Render
# ============================================================

def main() -> None:
    logger.info("🍪 Starting Red Eye Cookies Bot [webhook mode]")
    logger.info("PORT=%s  WEBHOOK_URL=%s", PORT, WEBHOOK_URL)

    app = build_app()

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{WEBHOOK_PATH}",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,          # Ignore queued msgs from downtime
    )


if __name__ == "__main__":
    main()
