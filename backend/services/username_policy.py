import re

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 32
USERNAME_FORMAT_MESSAGE = "用户名仅支持 3–32 位英文字母或数字"
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9]{3,32}")


def validate_registration_username(value: str) -> str:
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError(USERNAME_FORMAT_MESSAGE)
    return value
