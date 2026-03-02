#!/usr/bin/env python3
"""
Red Eye Cookies Bot - Full Telegram Sales Bot
Install: pip install python-telegram-bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
#  CONFIG — CHANGE THESE
# ============================================================
BOT_TOKEN   = "8440940013:AAFX8fxLTtZ2SUpc-KenhEdUrE2RRced58o"       # @BotFather token
ADMIN_ID    = 7616147846                    # Your Telegram numeric ID
SUPPORT_UN  = "@your_support_username"     # Support handle
CHANNEL_URL = "https://t.me/your_channel" # Your channel
CRYPTO_ADDR = "YOUR_BTC_WALLET"           # BTC address
USDT_ADDR   = "YOUR_USDT_TRC20_WALLET"   # USDT TRC20 address

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  IN-MEMORY STORES  (swap for SQLite/Postgres in production)
# ============================================================
user_orders: dict = {}   # order_id -> order dict
order_counter: list = [0]  # mutable counter

# ============================================================
#  PLANS
# ============================================================
PLANS = {
    # -------- WEEKLY --------
    "wk_basic": {
        "name": "Weekly Basic",   "tier": "WEEKLY",
        "duration": "7 Days",     "price": "$9.99",
        "emoji": "🟢",
        "features": [
            "1 Active Account",
            "Browser-in-Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "wk_pro": {
        "name": "Weekly Pro",     "tier": "WEEKLY",
        "duration": "7 Days",     "price": "$14.99",
        "emoji": "🔵",
        "features": [
            "3 Active Accounts",
            "Browser-in-Browser Support",
            "Email + Background Logo",
            "Long-Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    # -------- BI-WEEKLY --------
    "bw_basic": {
        "name": "Bi-Weekly Basic","tier": "BI-WEEKLY",
        "duration": "14 Days",    "price": "$17.99",
        "emoji": "🟡",
        "features": [
            "1 Active Account",
            "Browser-in-Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "bw_pro": {
        "name": "Bi-Weekly Pro",  "tier": "BI-WEEKLY",
        "duration": "14 Days",    "price": "$24.99",
        "emoji": "🟠",
        "features": [
            "5 Active Accounts",
            "Browser-in-Browser Support",
            "Email + Background Logo",
            "Long-Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    # -------- MONTHLY --------
    "mo_basic": {
        "name": "Monthly Basic",  "tier": "MONTHLY",
        "duration": "30 Days",    "price": "$29.99",
        "emoji": "🔴",
        "features": [
            "1 Active Account",
            "Browser-in-Browser Support",
            "Email Access Included",
            "Background Logo Grab",
            "Basic 24/7 Support",
        ],
    },
    "mo_pro": {
        "name": "Monthly Pro",    "tier": "MONTHLY",
        "duration": "30 Days",    "price": "$44.99",
        "emoji": "⚡",
        "features": [
            "10 Active Accounts",
            "Browser-in-Browser Support",
            "Email + Background Logo",
            "Long-Lasting Cookie Stability",
            "Priority 24/7 Support",
        ],
    },
    "mo_elite": {
        "name": "Monthly Elite",  "tier": "MONTHLY",
        "duration": "30 Days",    "price": "$69.99",
        "emoji": "👑",
        "features": [
            "Unlimited Accounts",
            "Browser-in-Browser Support",
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

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  Buy Now",         callback_data="buy_now"),
         InlineKeyboardButton("📋  Plans & Pricing", callback_data="plans")],
        [InlineKeyboardButton("📊  My Dashboard",    callback_data="dashboard"),
         InlineKeyboardButton("🎫  My Orders",       callback_data="my_orders")],
        [InlineKeyboardButton("💬  Support",         callback_data="support"),
         InlineKeyboardButton("ℹ️  About",           callback_data="about")],
        [InlineKeyboardButton("📢  Our Channel",     url=CHANNEL_URL)],
    ])


def kb_plans():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("━━━  WEEKLY PLANS  ━━━", callback_data="noop")],
        [InlineKeyboardButton("🟢 Basic  $9.99",  callback_data="plan_wk_basic"),
         InlineKeyboardButton("🔵 Pro  $14.99",   callback_data="plan_wk_pro")],
        [InlineKeyboardButton("━━  BI-WEEKLY PLANS  ━━", callback_data="noop")],
        [InlineKeyboardButton("🟡 Basic  $17.99", callback_data="plan_bw_basic"),
         InlineKeyboardButton("🟠 Pro  $24.99",   callback_data="plan_bw_pro")],
        [InlineKeyboardButton("━━━  MONTHLY PLANS  ━━━", callback_data="noop")],
        [InlineKeyboardButton("🔴 Basic  $29.99", callback_data="plan_mo_basic"),
         InlineKeyboardButton("⚡ Pro  $44.99",   callback_data="plan_mo_pro")],
        [InlineKeyboardButton("👑  Elite  $69.99  (BEST VALUE)", callback_data="plan_mo_elite")],
        [InlineKeyboardButton("🔙 Back",           callback_data="main_menu")],
    ])


def kb_plan_detail(plan_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Purchase This Plan", callback_data=f"buy_{plan_key}")],
        [InlineKeyboardButton("📋  All Plans", callback_data="plans"),
         InlineKeyboardButton("🔙  Menu",     callback_data="main_menu")],
    ])


def kb_payment(plan_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙  Pay with BTC",       callback_data=f"pay_btc_{plan_key}")],
        [InlineKeyboardButton("💲  Pay with USDT TRC20", callback_data=f"pay_usdt_{plan_key}")],
        [InlineKeyboardButton("🔙  Back to Plans",      callback_data="plans")],
    ])


def kb_support():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆘  Open Ticket",   callback_data="open_ticket")],
        [InlineKeyboardButton("📖  FAQ",            callback_data="faq"),
         InlineKeyboardButton("💬  Live Chat",      url=f"https://t.me/{SUPPORT_UN.lstrip('@')}")],
        [InlineKeyboardButton("🔙  Main Menu",      callback_data="main_menu")],
    ])


def kb_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙  Main Menu", callback_data="main_menu")]
    ])

# ============================================================
#  MESSAGE TEMPLATES
# ============================================================

WELCOME = """
🍪 *Welcome to Red Eye Cookies Bot!* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 *Your #1 Source for Premium Cookies*

✅  All Types of Links In Stock
✅  Fast & Secure Delivery
✅  Browser‑in‑Browser Support
✅  Background Logo & Email Included
✅  Long‑Lasting Cookies for Stability
✅  Results Delivered Directly to Telegram
✅  24/7 Support Team Ready to Assist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦  *7 Flexible Plans Available*
🟢 Weekly  |  🟡 Bi‑Weekly  |  👑 Monthly

👇 *Select an option to get started!*
"""

ABOUT = """
🍪 *About Red Eye Cookies* 🍪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 *Why Choose Us?*

🔐 *Fast & Secure* — Instant delivery right to your inbox

🌐 *Browser‑in‑Browser* — Full session compatibility

📦 *7 Flexible Plans* — Weekly, Bi‑Weekly & Monthly

🎨 *Logo & Email Grab* — Authentic session data

⏳ *Long‑Lasting Cookies* — Maximum stability built-in

🛡️ *24/7 Support* — Always here when you need us

📲 *User Dashboard* — Manage all orders in one place

📩 *Direct Telegram Delivery* — No external links needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Questions? Hit Support below!
"""

# ============================================================
#  HELPER: next order ID
# ============================================================

def next_order_id(user_id: int) -> str:
    order_counter[0] += 1
    return f"ORD-{user_id}-{order_counter[0]:05d}"

# ============================================================
#  /start
# ============================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start — {user.id} @{user.username}")
    await update.message.reply_text(
        WELCOME, parse_mode="Markdown", reply_markup=kb_main()
    )

# ============================================================
#  MAIN CALLBACK ROUTER
# ============================================================

async def callback_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    # ── NOOP (section headers) ──────────────────────────────
    if d == "noop":
        return

    # ── MAIN MENU ───────────────────────────────────────────
    if d == "main_menu":
        await q.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=kb_main())

    # ── BUY NOW / PLANS ─────────────────────────────────────
    elif d in ("buy_now", "plans"):
        hdr = "🛒 *Buy Now — Pick Your Plan*" if d == "buy_now" else "📋 *Plans & Pricing*"
        msg = f"""
{hdr}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every plan includes:
✅ Browser‑in‑Browser  ✅ Direct Telegram Delivery
✅ Email + Logo Access ✅ 24/7 Support
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_plans())

    # ── PLAN DETAIL ─────────────────────────────────────────
    elif d.startswith("plan_"):
        key = d[5:]
        p = PLANS.get(key)
        if not p:
            return
        feats = "\n".join(f"   ✅ {f}" for f in p["features"])
        msg = f"""
{p['emoji']} *{p['name']}* {p['emoji']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱  *Duration:* {p['duration']}
💵  *Price:*    {p['price']}
📦  *Tier:*     {p['tier']}

🗂 *What's Included:*
{feats}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Delivery: Instant to Telegram
🔐 Fully Encrypted Transfer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_plan_detail(key))

    # ── CHECKOUT (choose payment method) ────────────────────
    elif d.startswith("buy_"):
        key = d[4:]
        p = PLANS.get(key)
        if not p:
            return
        msg = f"""
💳 *Checkout — {p['name']}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Plan:     {p['name']}
⏱  Duration: {p['duration']}
💵 Amount:   *{p['price']}*

Select your payment method below 👇
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_payment(key))

    # ── PAYMENT (BTC / USDT) ────────────────────────────────
    elif d.startswith("pay_btc_") or d.startswith("pay_usdt_"):
        if d.startswith("pay_btc_"):
            method = "BTC"
            key    = d[8:]
            addr   = CRYPTO_ADDR
        else:
            method = "USDT (TRC20)"
            key    = d[9:]
            addr   = USDT_ADDR

        p = PLANS.get(key)
        if not p:
            return

        user     = q.from_user
        oid      = next_order_id(user.id)
        user_orders[oid] = {
            "user_id":  user.id,
            "username": user.username or "N/A",
            "plan_key": key,
            "plan":     p["name"],
            "price":    p["price"],
            "method":   method,
            "status":   "Pending",
        }

        msg = f"""
📝 *Order Created Successfully!* 📝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆔  Order ID:  `{oid}`
📦  Plan:      {p['name']}
💵  Amount:    {p['price']}
💳  Method:    {method}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 *Send Exact Amount To:*
`{addr}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 *After Payment — 3 Steps:*
1️⃣  Screenshot or copy TX hash
2️⃣  Message {SUPPORT_UN} with your Order ID
3️⃣  Cookies delivered in *5–15 min* ✅

⚠️  Order expires in *30 minutes*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_back())

        # Admin alert
        try:
            admin_msg = (
                f"🔔 *NEW ORDER*\n"
                f"━━━━━━━━━━━━━\n"
                f"🆔  `{oid}`\n"
                f"👤  @{user.username}  (`{user.id}`)\n"
                f"📦  {p['name']}\n"
                f"💵  {p['price']}\n"
                f"💳  {method}\n"
                f"━━━━━━━━━━━━━\n"
                f"Use /complete {oid} when paid."
            )
            await ctx.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Admin notify failed: {e}")

    # ── DASHBOARD ───────────────────────────────────────────
    elif d == "dashboard":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]
        total  = len(orders)
        done   = sum(1 for _, o in orders if o["status"] == "Completed")
        pending= total - done

        recent = ""
        for oid, o in orders[-5:][::-1]:
            ico = "✅" if o["status"] == "Completed" else "⏳"
            recent += f"{ico}  `{oid}`  —  {o['plan']}  —  {o['price']}\n"
        if not recent:
            recent = "📭 No orders yet — buy a plan to get started!"

        msg = f"""
📊 *My Dashboard* 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤  {user.first_name}
🆔  User ID:  `{user.id}`

📦  Total Orders:  {total}
✅  Completed:     {done}
⏳  Pending:       {pending}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 *Recent Orders:*
{recent}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 New Order",   callback_data="plans"),
             InlineKeyboardButton("🎫 All Orders",  callback_data="my_orders")],
            [InlineKeyboardButton("💬 Support",     callback_data="support"),
             InlineKeyboardButton("🔙 Main Menu",   callback_data="main_menu")],
        ])
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)

    # ── ALL ORDERS ──────────────────────────────────────────
    elif d == "my_orders":
        user   = q.from_user
        orders = [(oid, o) for oid, o in user_orders.items() if o["user_id"] == user.id]

        if not orders:
            body = "📭 No orders found.\n\nPurchase a plan to get started!"
        else:
            body = ""
            for oid, o in orders[::-1]:
                ico   = "✅" if o["status"] == "Completed" else "⏳"
                body += (
                    f"\n{ico} *{oid}*\n"
                    f"   Plan:   {o['plan']}\n"
                    f"   Price:  {o['price']}\n"
                    f"   Status: {o['status']}\n"
                )

        await q.edit_message_text(
            f"🎫 *My Orders*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{body}",
            parse_mode="Markdown", reply_markup=kb_back()
        )

    # ── SUPPORT ─────────────────────────────────────────────
    elif d == "support":
        msg = f"""
💬 *Support Center* 💬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🕐 *24/7 Support Available*
⚡ Avg Response: < 15 minutes
🌟 Satisfaction Rate: 99.8%

📌 We handle:
  • Delivery issues
  • Technical problems
  • Billing / payment queries
  • General questions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Live chat: {SUPPORT_UN}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_support())

    # ── OPEN TICKET ─────────────────────────────────────────
    elif d == "open_ticket":
        user = q.from_user
        msg = f"""
🎟 *Support Ticket Created* 🎟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆔  Your ID:    `{user.id}`
👤  Username:  @{user.username or 'N/A'}

📌 *Next Steps:*
1️⃣  Message {SUPPORT_UN}
2️⃣  Include your User ID: `{user.id}`
3️⃣  Describe your issue clearly

⚡ Response within *15 minutes*!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_back())

    # ── FAQ ─────────────────────────────────────────────────
    elif d == "faq":
        msg = """
📖 *FAQ — Frequently Asked Questions* 📖
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ *How fast is delivery?*
✅  5–15 min after payment confirmation

❓ *How long do cookies last?*
✅  Plan-dependent; built for max stability

❓ *Accepted payment methods?*
✅  BTC, USDT TRC20

❓ *Do you refund?*
✅  Yes — within 24 hrs if delivery fails

❓ *What is Browser‑in‑Browser?*
✅  Full browser session data — no partial cookies

❓ *Can I upgrade my plan?*
✅  Yes — contact support anytime

❓ *Is my data safe?*
✅  100% encrypted delivery, no logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb_support())

    # ── ABOUT ───────────────────────────────────────────────
    elif d == "about":
        await q.edit_message_text(ABOUT, parse_mode="Markdown", reply_markup=kb_back())

# ============================================================
#  ADMIN COMMANDS
# ============================================================

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    total   = len(user_orders)
    pending = sum(1 for o in user_orders.values() if o["status"] == "Pending")
    done    = total - pending

    msg = (
        f"🔧 *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total Orders:  {total}\n"
        f"⏳ Pending:        {pending}\n"
        f"✅ Completed:      {done}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Commands:\n"
        f"`/complete <order_id>` — Mark completed & notify user\n"
        f"`/orders`              — List last 20 orders\n"
        f"`/deliver <user_id> <text>` — Send cookies to user\n"
        f"`/broadcast <msg>`    — Message all customers\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_complete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /complete <order_id>")
        return

    oid = ctx.args[0].upper()
    if oid not in user_orders:
        await update.message.reply_text(f"❌ Order `{oid}` not found.", parse_mode="Markdown")
        return

    user_orders[oid]["status"] = "Completed"
    uid   = user_orders[oid]["user_id"]
    plan  = user_orders[oid]["plan"]

    try:
        await ctx.bot.send_message(
            uid,
            f"🍪 *Order Fulfilled!*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔  `{oid}`\n"
            f"📦  {plan}\n\n"
            f"Your cookies have been delivered to this chat.\n"
            f"Enjoy! If you need help, use /start → Support.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"User notify failed: {e}")

    await update.message.reply_text(f"✅ Order `{oid}` marked complete & user notified.", parse_mode="Markdown")


async def cmd_deliver(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Send cookie payload directly to user: /deliver <user_id> <content>"""
    if update.effective_user.id != ADMIN_ID:
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /deliver <user_id> <cookie_data_or_text>")
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
            f"✅ Import into your browser. Questions? /start → Support.",
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Delivered to user `{uid}`.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not user_orders:
        await update.message.reply_text("No orders yet.")
        return

    lines = "📋 *Last 20 Orders*\n━━━━━━━━━━━━━━━━━━\n"
    for oid, o in list(user_orders.items())[-20:][::-1]:
        ico   = "✅" if o["status"] == "Completed" else "⏳"
        lines += f"{ico} `{oid}` | @{o['username']} | {o['plan']} | {o['price']}\n"

    await update.message.reply_text(lines, parse_mode="Markdown")


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    text    = " ".join(ctx.args)
    targets = set(o["user_id"] for o in user_orders.values())
    sent = 0
    for uid in targets:
        try:
            await ctx.bot.send_message(uid, f"📢 *Announcement*\n\n{text}", parse_mode="Markdown")
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {sent} user(s).")


# ============================================================
#  FALLBACK
# ============================================================

async def cmd_unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Unknown command. Tap the button below to open the menu.",
        reply_markup=kb_main()
    )

# ============================================================
#  ENTRY POINT
# ============================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start",     cmd_start))

    # Admin commands
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("complete",  cmd_complete))
    app.add_handler(CommandHandler("deliver",   cmd_deliver))
    app.add_handler(CommandHandler("orders",    cmd_orders))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    # Catch-all for unknown text/commands
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    logger.info("🍪 Red Eye Cookies Bot is LIVE — polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
