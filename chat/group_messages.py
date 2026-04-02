# Standard library imports
from datetime import datetime


def format_chat_message(room_id: int, user_id: int, anonymous: bool, message: str, message_id: int, upvotes: int, downvotes: int, new: bool, edited: bool, date: datetime, latest_date: datetime, attachments: dict):
    """
    Return formatted dict with message data.
    Used to format messages loaded from DB or messages sent by user to chat
    """
    return {
        "type": "chat.message",
        "room_id": room_id,
        "user_id": user_id,
        "message_id": message_id,
        "message": message,
        "anonymous": anonymous,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "new": new,
        "edited": edited,
        "timestamp": int(date.timestamp()) * 1000,  # unix to ms
        "latest_timestamp": int(latest_date.timestamp()) * 1000,  # unix to ms
        "attachments": attachments,
    }
