import json
import logging
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON 格式的日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": f"{record.filename}:{record.lineno}",
        }
        # 添加额外字段（如果有）
        if hasattr(record, "chat_id"):
            log_obj["chat_id"] = record.chat_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# 全局监听器引用，用于生命周期管理
_listener: Optional[QueueListener] = None


def setup_logging(
    debug: bool = False,
    log_level: str = "INFO",
    log_async: bool = True,
    log_format: str = "text",
    log_access: bool = False,
) -> Optional[QueueListener]:
    """
    配置日志系统

    Args:
        debug: 是否开启调试模式
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_async: 是否使用异步队列日志（提高性能）
        log_format: 日志格式 (text 或 json)
        log_access: 是否启用 uvicorn/hypercorn access 日志

    Returns:
        QueueListener 实例（如果使用异步日志），需要在应用关闭时调用 stop()
    """
    global _listener

    # 确保日志目录存在
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True, parents=True)

    # 解析日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    if debug:
        level = logging.DEBUG

    # 创建格式化器
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    # 创建文件 handler
    file_handler = RotatingFileHandler(
        filename=LOG_DIR / "index.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    if log_format == "text":
        console_formatter = ColoredFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    else:
        console_formatter = formatter
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if log_async:
        # 使用队列异步日志
        log_queue = Queue(-1)  # 无界队列
        queue_handler = QueueHandler(log_queue)
        root_logger.addHandler(queue_handler)

        # 启动队列监听器（后台线程处理实际 I/O）
        _listener = QueueListener(
            log_queue, file_handler, console_handler, respect_handler_level=True
        )
        _listener.start()
    else:
        # 同步日志模式
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        _listener = None

    # 配置 Uvicorn 日志
    _configure_uvicorn_logging(level, log_access, formatter if not log_async else None)

    # 配置 Hypercorn 日志
    _configure_hypercorn_logging(
        level, log_access, formatter if not log_async else None
    )

    logging.info(
        "日志系统初始化完成 (level=%s, async=%s, format=%s)",
        log_level,
        log_async,
        log_format,
    )
    return _listener


def _configure_uvicorn_logging(
    level: int,
    log_access: bool,
    formatter: Optional[logging.Formatter] = None,
):
    """配置 Uvicorn 相关日志"""
    # Uvicorn 主日志
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(level)

    # Uvicorn 错误日志
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.setLevel(level)

    # Uvicorn 访问日志 - 彻底禁用或启用
    uvicorn_access = logging.getLogger("uvicorn.access")
    if log_access:
        uvicorn_access.setLevel(logging.INFO)
        uvicorn_access.propagate = True
    else:
        # 彻底禁用访问日志：清除所有 handlers 并设置高级别
        uvicorn_access.handlers.clear()
        uvicorn_access.setLevel(logging.WARNING)
        uvicorn_access.propagate = False
        # 添加 NullHandler 防止 "No handler found" 警告
        uvicorn_access.addHandler(logging.NullHandler())

    # 确保 Uvicorn 日志使用我们的 handler（如果不使用 QueueHandler 模式）
    if formatter:
        for logger_name in ["uvicorn", "uvicorn.error"]:
            uv_logger = logging.getLogger(logger_name)
            # 保留 Uvicorn 的 handler 配置，但确保级别正确
            uv_logger.propagate = True


def reconfigure_uvicorn_logging(log_access: bool = False):
    """
    在 Uvicorn 启动后重新配置日志
    用于确保 Uvicorn 不会覆盖我们的配置
    """
    uvicorn_access = logging.getLogger("uvicorn.access")
    if not log_access:
        uvicorn_access.handlers.clear()
        uvicorn_access.setLevel(logging.WARNING)
        uvicorn_access.propagate = False
        uvicorn_access.addHandler(logging.NullHandler())


def _configure_hypercorn_logging(
    level: int,
    log_access: bool,
    formatter: Optional[logging.Formatter] = None,
):
    """配置 Hypercorn 相关日志"""
    # Hypercorn 主日志
    hypercorn_logger = logging.getLogger("hypercorn")
    hypercorn_logger.setLevel(level)

    # Hypercorn 错误日志
    hypercorn_error = logging.getLogger("hypercorn.error")
    hypercorn_error.setLevel(level)

    # Hypercorn 访问日志 - 彻底禁用或启用
    hypercorn_access = logging.getLogger("hypercorn.access")
    if log_access:
        hypercorn_access.setLevel(logging.INFO)
        hypercorn_access.propagate = True
    else:
        # 彻底禁用访问日志：清除所有 handlers 并设置高级别
        hypercorn_access.handlers.clear()
        hypercorn_access.setLevel(logging.WARNING)
        hypercorn_access.propagate = False
        # 添加 NullHandler 防止 "No handler found" 警告
        hypercorn_access.addHandler(logging.NullHandler())

    # 确保 Hypercorn 日志使用我们的 handler（如果不使用 QueueHandler 模式）
    if formatter:
        for logger_name in ["hypercorn", "hypercorn.error"]:
            hc_logger = logging.getLogger(logger_name)
            # 保留 Hypercorn 的 handler 配置，但确保级别正确
            hc_logger.propagate = True


def reconfigure_hypercorn_logging(log_access: bool = False):
    """
    在 Hypercorn 启动后重新配置日志
    用于确保 Hypercorn 不会覆盖我们的配置
    """
    hypercorn_access = logging.getLogger("hypercorn.access")
    if not log_access:
        hypercorn_access.handlers.clear()
        hypercorn_access.setLevel(logging.WARNING)
        hypercorn_access.propagate = False
        hypercorn_access.addHandler(logging.NullHandler())


def stop_logging():
    """停止日志监听器（应用关闭时调用）"""
    global _listener
    if _listener:
        _listener.stop()
        _listener = None
        logging.info("日志系统已关闭")
