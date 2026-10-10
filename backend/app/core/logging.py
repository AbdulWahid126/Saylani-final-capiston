import logging
import re
import sys

# Sensitive pattern regexes to redact from logs
SENSITIVE_PATTERNS = [
    re.compile(
        r"(password|secret|token|key|credential|authorization)[\"']?\s*[:=]\s*[\"']?([^\"'\s,]+)",
        re.IGNORECASE,
    ),
    re.compile(r"Bearer\s+([A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*)", re.IGNORECASE),
]


class SecretMaskingFilter(logging.Filter):
    """Sanitizes sensitive information (passwords, tokens, keys) from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.mask_secrets(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.mask_secrets(str(arg)) for arg in record.args)
        return True

    @staticmethod
    def mask_secrets(text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1=***REDACTED***", text)
        return text


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures structured console logging with secret hygiene."""
    logger = logging.getLogger("trading_copilot")
    logger.setLevel(level)

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(module)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretMaskingFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
