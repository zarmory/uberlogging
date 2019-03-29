# -*- coding: utf-8 -*-

import os
import string
import sys
from copy import deepcopy
from enum import Enum
import logging
from logging.config import dictConfig

import coloredlogs
import structlog
from humanfriendly.terminal import ansi_wrap
from pythonjsonlogger import jsonlogger
from structlog import get_logger


__all__ = (
    "get_logger",
    "configure",
    "default_fmt",
    "default_datefmt",
    "style",
)

# NOTE: Only "{" style is supported
# "context" field is always provided (it's an empty string for stdlib logger")
default_fmt = "{asctime}.{msecs:03.0f} " + \
              "{name:<15} {levelname:<7} ## " + \
              "{message}    {context}    {module}.{funcName}:{lineno}"
default_datefmt = "%Y-%m-%dT%H:%M:%S"
simple_fmt_name = "simple"
simple_colors_fmt_name = "simple_colors"
simple_json_fmt_name = "simple_json"


class Style(Enum):
    auto = 0
    text_auto = 1
    json = 10
    text_color = 20
    text_no_color = 30


style_to_fmt_name = {
    Style.json: simple_json_fmt_name,
    Style.text_color: simple_colors_fmt_name,
    Style.text_no_color: simple_fmt_name,
}


def default_conf(fmt=default_fmt, datefmt=default_datefmt):
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            simple_fmt_name: {
                "format": fmt,
                "datefmt": datefmt,
                "class": "uberlogging.Formatter",
            },
            simple_colors_fmt_name: {
                "format": fmt,
                "datefmt": datefmt,
                "class": "uberlogging.ColoredFormatter",
            },
            simple_json_fmt_name: {
                "format": fmt,
                "datefmt": datefmt,
                "class": "uberlogging.SeverityJsonFormatter",
            }
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": simple_fmt_name,
            }
        },
        "root": {
            "level": None,
            "handlers": ["console"],
        },
    }


def configure(style=Style.auto,
              fmt=default_fmt, datefmt=default_datefmt,
              logger_confs: dict = None,
              logger_confs_list: list = None,
              cache_structlog_loggers=True,
              full_conf: dict = None,
              root_level=logging.INFO):
    """
    Configure both structlog and stdlib logger libraries
    with sane defaults.

    :param style:
        Force custom style as in `uberlogging.Style`. Style is
        autodetected by default

    :param fmt:
        Custom message formatting to use. In stdlib logging format.
        This is a shortcut to change configration quickly without
        fiddling with logging configuration in full

    :param datefmt:
        Custom timestamp formatting to use. In stdlib logging format.
        This is a shortcut to change configuration quickly without
        fiddling with logging configuration in full

    :param logger_confs:
        Configuration for additional loggers, e.g.::

            logger_confs = {
                "requests": {"level": "DEBUG"}
            }

    :param logger_confs_list:
        Configuration for additional loggers in list format.
        The list will be converted to logger_confs dict (overriding existing key)
        The rationale is overcome limitation of configuration libraries that don't
        allow config property name to container ".", therefore inhibiting configuration
        of hierarchical loggers

        Example::

            logger_confs_list = [
                {"name": "foo", "level": "INFO"},
                {"name": "foo.bar", "level": "ERROR"},
            }


    :param cache_structlog_loggers:
        Enable/disabled caching of structlog loggers as described
        in `documentation <http://www.structlog.org/en/stable/performance.html>`_.
        You should generally leave it to True, unless, e.g. writing tests

    :param full_conf:
        Provide your own dictConfig dictionary - hard override for everything except
        of structlog key-val formatting

    :param root_level:
        Set log level of the root logger. Defaults to logging.INFO.
    """

    actual_style = _detect_style(style)
    formatter_name = style_to_fmt_name[actual_style]
    colored = (actual_style == Style.text_color)

    fmt = os.environ.get("UBERLOGGING_MESSAGE_FORMAT") or fmt
    conf = full_conf or _build_conf(fmt, datefmt, logger_confs, logger_confs_list, formatter_name, root_level)
    _configure_structlog(colored, cache_structlog_loggers)
    _configure_stdliblog(conf)


def _detect_style(style):
    if os.environ.get("UBERLOGGING_FORCE_TEXT_COLOR"):
        style = Style.text_color
    elif os.environ.get("UBERLOGGING_FORCE_TEXT_NO_COLOR"):
        style = Style.text_no_color
    elif os.environ.get("UBERLOGGING_FORCE_TEXT"):
        style = Style.text_auto

    if style not in (Style.auto, Style.text_auto):
        return style

    isatty = sys.stderr.isatty()
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
        KeyValueRendererWithFlatEventColors(colored),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=cache_loggers,
    )


def _configure_stdliblog(conf):
    dictConfig(conf)


def _build_conf(fmt, datefmt, logger_confs, logger_confs_list, formatter_name, root_level):
    conf = default_conf(fmt, datefmt)
    logger_confs = logger_confs or {}
    for lconf in (logger_confs_list or []):
        name = lconf.pop("name")
        logger_confs[name] = lconf
    if logger_confs:
        conf["loggers"] = logger_confs
    for handler in conf["handlers"].values():
        handler["formatter"] = formatter_name
    conf["root"]["level"] = logging.getLevelName(root_level)
    return conf


class SeverityJsonFormatter(jsonlogger.JsonFormatter):
    def parse(self):
        field_spec = string.Formatter().parse(self._fmt)
        return [s[1] for s in field_spec]

    def add_fields(self, log_record, record, message_dict):
        # Fix for Stackdriver that expects loglevel in "severity" field
        super().add_fields(log_record, record, message_dict)
        log_record["severity"] = record.levelname


class Formatter(logging.Formatter):
    # Requesting new Python3 style formatting
    def __init__(self, fmt=None, datefmt=None, style="{", **kwargs):
        style = "{"
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, **kwargs)

    # Since we want to provide uniformity between stdlib and structlog
    # We need to make sure that "context" attribute is always present
    # in the log record - this is to enable using unified formatting style.
    # If structlog is used it will inject the "context" as part of the
    # "extra" dictionary. However if stdlib is used, we need to fullfil it
    # "manually" here.
    def format(self, record):
        if not hasattr(record, "context"):
            record.context = ""
        return super().format(record)


class ColoredFormatter(Formatter, coloredlogs.ColoredFormatter):
    custom_field_styles = deepcopy(coloredlogs.DEFAULT_FIELD_STYLES)
    custom_field_styles.update({
        "module": {"color": "white", "faint": True},
        "funcName": {"color": "white", "faint": True},
        "lineno": {"color": "white", "faint": True},
    })

    # Exposing logging.Formatter interface since we don't initialize this class by ourselves
    def __init__(self, fmt=None, datefmt=None, style="{"):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, field_styles=self.custom_field_styles)


class KeyValueRendererWithFlatEventColors:
    style_key = {"color": "cyan"}
    style_val = {"color": "magenta"}

    def __init__(self, color=True):
        self.color = color

    def __call__(self, _, __, event_dict):
        ev = event_dict.pop("event") if "event" in event_dict else ""
        if not isinstance(ev, str):
            ev = str(ev)

        context = " ".join(
            (ansi_wrap(key, **self.style_key) if self.color else key)
            + "="
            + (ansi_wrap(repr(event_dict[key]), **self.style_val) if self.color else repr(event_dict[key]))

            for key in event_dict.keys() if key != "exc_info"
        )

        return {"msg": ev, "exc_info": event_dict.get("exc_info"), "extra": {"context": context}}
