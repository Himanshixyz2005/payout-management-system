from typing import Any


def success_response(message: str, data: Any = None):
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(message: str):
    return {
        "success": False,
        "message": message
    }