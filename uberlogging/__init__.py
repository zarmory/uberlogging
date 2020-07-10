# -*- coding: utf-8 -*-

import logging
import os
import string
import sys
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from logging.config import dictConfig
from typing import Any, ClassVar, List, Tuple

import coloredlogs
import structlog
from humanfriendly.terminal import ansi_wrap
from pythonjsonlogger import jsonlogger

__all__ = (
    "get_logger",
    "configure",
    "default_fmt",
    "default_datefmt",
    "style",
)

# NOTE: Only "{" style is supported
# "context" field is always provided (it's an empty string for stdlib logger")
default_fmt = ("{asctime}.{msecs:03.0f} "
               + "{name:<15} {levelname:<7} ## "
               + "{message}{context}{contextvars}    {module}.{funcName}:{lineno}")
default_datefmt = "%Y-%m-%dT%H:%M:%S"

padding = "    "


def get_logger(*args, **kwargs) -> None:
    raise AttributeError("uberlogging.get_logger() was deprecated and removed. "
                         + "It did nothing but hoisting structlog.get_logger. "
                         + "So use just that instead.")


class Style(Enum):
    auto = 0
    text_auto = 1
    json = 10
    text_color = 20
    text_no_color = 30


def _style_to_formatter(style):
    return {
        Style.json: SeverityJsonFormatter,
        Style.text_color: ColoredFormatter,
        Style.text_no_color: Formatter,
    }.get(style)


def configure(style=Style.auto,
              fmt=default_fmt, datefmt=default_datefmt,
              logger_confs: dict = None,
              logger_confs_list: list = None,
              cache_structlog_loggers=True,
              root_level=logging.INFO,
              stream=sys.stderr,
              contextvars: Tuple[ContextVar] = ()):
    """
    Configure both structlog and stdlib logger libraries
    with sane defaults.

    :param style:
        Force custom style as in `uberlogging.Style`. Style is
        autodetected by default.

    :param fmt:
        Custom message formatting to use. In stdlib logging format.
        This is a shortcut to change configration quickly without
        fiddling with logging configuration in full.

    :param datefmt:
        Custom timestamp formatting to use. In stdlib logging format.
        This is a shortcut to change configuration quickly without
        fiddling with logging configuration in full.

    :param logger_confs:
        Configuration for additional loggers, e.g.::

            logger_confs = {
                "requests": {"level": "DEBUG"}
            }

    :param logger_confs_list:
        Configuration for additional loggers in list format.
        The list will be converted to logger_confs dict (overriding existing key)
        The rationale is overcome limitation of configuration libraries that don't
        allow config property name to contain ".", therefore inhibiting configuration
        of hierarchical loggers.

        Example::

            logger_confs_list = [
                {"name": "foo", "level": "INFO"},
                {"name": "foo.bar", "level": "ERROR"},
            }

    :param cache_structlog_loggers:
        Enable/disabled caching of structlog loggers as described
        in `documentation <http://www.structlog.org/en/stable/performance.html>`_.
        You should generally leave it to True, unless, e.g. writing tests.

    :param root_level:
        Set log level of the root logger. Defaults to logging.INFO.

    :param stream:
        Stream to use for logging.StreamHandler class. Defaults to sys.stderr. Useful
        for programatic logging stream redirection in console scripts.

    :param contextvars:
        Provided contextvars name/value will be added as part of the log message
        (via "contextvars" section).

        **NOTE**: Python 3.7.1+ only. ContextVar.name didn't appear till then.

    """

    actual_style = _detect_style(style, stream)
    colored = (actual_style == Style.text_color)

    fmt = os.environ.get("UBERLOGGING_MESSAGE_FORMAT") or fmt
    conf = _build_conf(fmt, datefmt, logger_confs, logger_confs_list, actual_style, root_level, contextvars, stream)
    _configure_structlog(colored, cache_structlog_loggers)
    _configure_stdliblog(conf)


def _detect_style(style, stream):
    if os.environ.get("UBERLOGGING_FORCE_TEXT_COLOR"):
        style = Style.text_color
    elif os.environ.get("UBERLOGGING_FORCE_TEXT_NO_COLOR"):
        style = Style.text_no_color
    elif os.environ.get("UBERLOGGING_FORCE_TEXT"):
        style = Style.text_auto

    if style not in (Style.auto, Style.text_auto):
        return style

    try:
        isatty = stream.isatty()
    except AttributeError:
        isatty = False

    force_text = (style == Style.text_auto)
    use_json = not (isatty or force_text)
    colored = isatty and not use_json

    if use_json:
        return Style.json
    elif colored:
        return Style.text_color
    else:
        return Style.text_no_color


def _configure_structlog(colored, cache_loggers):
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        # NOTE: We deliberatly flatten key/val structlog parameters
        # into a flat string - it's easier to read in log message
        # (both local and aggregated, e.g. Graylog) since fields
        # are highly dynamic and I prefer to track important stuff through
        # metrics
        KeyValueRendererWithFlatEventColors(renderer=ContextRenderer(colored)),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=cache_loggers,
    )


def _configure_stdliblog(conf):
    dictConfig(conf)


def _build_conf(fmt, datefmt, logger_confs, logger_confs_list, style: Style, root_level, contextvars, stream):
    formatter_class = _style_to_formatter(style)
    formatter = formatter_class(fmt=fmt, datefmt=datefmt, contextvars=contextvars)
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "current": {
                "()": lambda: formatter,
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "current",
                "stream": stream
            }
        },
        "root": {
            "level": logging.getLevelName(root_level),
            "handlers": ["console"],
        },
    }
    logger_confs = logger_confs or {}
    for lconf in (logger_confs_list or []):
        name = lconf.pop("name")
        logger_confs[name] = lconf
    if logger_confs:
        conf["loggers"] = logger_confs
    return conf


class SeverityJsonFormatter(jsonlogger.JsonFormatter):

    def __init__(self, *args, contextvars: Tuple[ContextVar] = (), **kwargs):
        # Requesting new Python3 style formatting
        kwargs["style"] = "{"
        self.contextvars = contextvars
        self.renderer = kwargs.pop("renderer", ContextRenderer(color=False))
        super().__init__(*args, **kwargs)

    def parse(self):
        field_spec = string.Formatter().parse(self._fmt)
        return [s[1] for s in field_spec]

    def add_fields(self, log_record, record, message_dict):
        # Fix for Stackdriver that expects loglevel in "severity" field
        super().add_fields(log_record, record, message_dict)
        log_record["severity"] = record.levelname

    def format(self, record):
        if self.contextvars:
            record.contextvars = self.renderer.render_contextvars(self.contextvars)
        return super().format(record)


class Formatter(logging.Formatter):
    # Requesting new Python3 style formatting
    def __init__(self, fmt=None, datefmt=None, style="{", contextvars: Tuple[ContextVar] = (), **kwargs):
        style = "{"
        self.contextvars = contextvars
        self.renderer = kwargs.pop("renderer", ContextRenderer(color=False))
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, **kwargs)

    # Since we want to provide uniformity between stdlib and structlog
    # We need to make sure that "context" attribute is always present
    # in the log record - this is to enable using unified formatting style.
    # If structlog is used it will inject the "context" as part of the
    # "extra" dictionary. However if stdlib is used, we need to fullfil it
    # "manually" here. Same for "contextvars" attribute.
    def format(self, record):
        if not hasattr(record, "context"):
            record.context = ""
        if self.contextvars:
            record.contextvars = ((" " if record.context else padding)
                                  + self.renderer.render_contextvars(self.contextvars))
        else:
            record.contextvars = ""
        return super().format(record)


class ColoredFormatter(Formatter, coloredlogs.ColoredFormatter):
    custom_field_styles = deepcopy(coloredlogs.DEFAULT_FIELD_STYLES)
    custom_field_styles.update({
        "module": {"color": "white", "faint": True},
        "funcName": {"color": "white", "faint": True},
        "lineno": {"color": "white", "faint": True},
    })

    # Exposing logging.Formatter interface since we don't initialize this class by ourselves
    def __init__(self, fmt=None, datefmt=None, style="{", contextvars: Tuple[ContextVar] = (), **kwargs):
        renderer = kwargs.pop("renderer", ContextRenderer(color=True))
        super().__init__(fmt=fmt, datefmt=datefmt, style=style,
                         field_styles=self.custom_field_styles,
                         contextvars=contextvars, renderer=renderer, **kwargs)


@dataclass
class ContextRenderer:
    style_key: ClassVar[dict] = {"color": "cyan"}
    style_val: ClassVar[dict] = {"color": "magenta"}

    color: bool

    def format_item(self, key: str, val: Any) -> str:
        return "{}={}".format(
            (ansi_wrap(key, **self.style_key) if self.color else key),
            (ansi_wrap(repr(val), **self.style_val) if self.color else repr(val))
        )

    def render_contextvars(self, vars: Tuple[ContextVar]) -> str:
        ctx_items: List[str] = []
        for var in vars:
            try:
                ctx_items.append(self.format_item(var.name, var.get()))
            except LookupError:  # contextvar is not set - ignoring
                continue
        return " ".join(ctx_items)


@dataclass
class KeyValueRendererWithFlatEventColors:
    renderer: ContextRenderer

    def __call__(self, _, __, event_dict):
        ev = event_dict.pop("event") if "event" in event_dict else ""
        if not isinstance(ev, str):
            ev = str(ev)

        context = " ".join(
            self.renderer.format_item(key, val)

            for key, val in event_dict.items() if key != "exc_info"
        )

        if context:
            context = padding + context

        return {"msg": ev, "exc_info": event_dict.get("exc_info"), "extra": {"context": context}}
