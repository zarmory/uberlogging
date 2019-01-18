# -*- coding: utf-8 -*-

import os
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

default_fmt = "%(asctime)s.%(msecs)03d: " + \
              "%(name)-15s %(levelname)-5s ## " + \
              "%(message)s     %(module)s.%(funcName)s:%(lineno)d"
default_datefmt = "%Y-%m-%dT%H:%M:%S"
simple_fmt_name = "simple"
simple_colors_fmt_name = "simple_colors"
simple_json_fmt_name = "simple_json"


class Style(Enum):
    auto = 0
    json = 1
    text_color = 2
    text_no_color = 3


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
                "class": "logging.Formatter",
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

    conf = full_conf or _build_conf(fmt, datefmt, logger_confs, logger_confs_list, formatter_name, root_level)
    _configure_structlog(colored, cache_structlog_loggers)
    _configure_stdliblog(conf)


def _detect_style(style):
    if style != Style.auto:
        return style

    isatty = sys.stderr.isatty()
    force_text = True if os.environ.get("UBERLOGGING_FORCE_TEXT") else False
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
    def add_fields(self, log_record, record, message_dict):
        # Fix for Stackdriver that expects loglevel in "severity" field
        super().add_fields(log_record, record, message_dict)
        log_record["severity"] = record.levelname


class ColoredFormatter(coloredlogs.ColoredFormatter):
    custom_field_styles = deepcopy(coloredlogs.DEFAULT_FIELD_STYLES)
    custom_field_styles.update({
        "module": {"color": "white", "faint": True},
        "funcName": {"color": "white", "faint": True},
        "lineno": {"color": "white", "faint": True},
    })

    # Exposing logging.Formatter interface since we don't initialize this class by ourselves
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, field_styles=self.custom_field_styles)


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

        event = "".join([
            ev,
            "    ",
            context,
        ])
        return {"msg": event, "exc_info": event_dict.get("exc_info")}
