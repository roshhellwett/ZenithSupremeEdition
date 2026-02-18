from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from core.logger import setup_logger

logger = setup_logger("SUPPORT_NOTIFY")

bot_instance = None


def set_notification_bot(app: Application):
    global bot_instance
    bot_instance = app.bot


async def notify_user_on_admin_reply(user_id: int, ticket_id: int, subject: str, admin_response: str):
    if not bot_instance:
        logger.warning("Bot instance not set for notifications")
        return False

    try:
        response_preview = admin_response[:200] + "..." if len(admin_response) > 200 else admin_response
        
        keyboard = [
            [InlineKeyboardButton("💬 Reply to Ticket", callback_data=f"ticket_reply_{ticket_id}")],
            [InlineKeyboardButton("📋 View Ticket", callback_data=f"ticket_view_{ticket_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "🎫 <b>New Response on Your Ticket</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Ticket #{ticket_id}</b>: {subject}\n\n"
            f"<b>Admin Response:</b>\n{response_preview}\n\n"
            "⏰ <i>Please reply within 24 hours or the ticket will be auto-closed.</i>\n\n"
            "💡 <i>Need more time? Just reply to keep the ticket active.</i>"
        )

        await bot_instance.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        logger.info(f"Notification sent to user {user_id} for ticket {ticket_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        return False


async def send_24h_reminder(user_id: int, ticket_id: int, subject: str):
    if not bot_instance:
        return False

    try:
        keyboard = [
            [InlineKeyboardButton("💬 Reply Now", callback_data=f"ticket_reply_{ticket_id}")],
            [InlineKeyboardButton("✅ Mark as Resolved", callback_data=f"ticket_close_user_{ticket_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "⏰ <b>Reminder: Ticket Closing Soon</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Ticket #{ticket_id}</b>: {subject}\n\n"
            "⚠️ <b>This ticket will be auto-closed in 1 hour</b> due to no response.\n\n"
            "If your issue is resolved, you can ignore this message or click 'Mark as Resolved'.\n"
            "To keep the ticket open, simply reply to this message."
        )

        await bot_instance.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        logger.info(f"24h reminder sent to user {user_id} for ticket {ticket_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send reminder to user {user_id}: {e}")
        return False


async def notify_ticket_auto_closed(user_id: int, ticket_id: int, subject: str):
    if not bot_instance:
        return False

    try:
        keyboard = [
            [InlineKeyboardButton("🎫 Create New Ticket", callback_data="support_new_ticket")],
            [InlineKeyboardButton("📋 My Tickets", callback_data="support_my_tickets")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "🔒 <b>Ticket Auto-Closed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Ticket #{ticket_id}</b>: {subject}\n\n"
            "<i>This ticket has been automatically closed due to no response within 24 hours.</i>\n\n"
            "If you still need help, feel free to create a new ticket."
        )

        await bot_instance.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        logger.info(f"Auto-close notification sent to user {user_id} for ticket {ticket_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to notify user {user_id} about auto-close: {e}")
        return False
