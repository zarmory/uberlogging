import logging
import os

import uberlogging


def main():
    logger = uberlogging.get_logger()

    # NOTE: using cache_structlog_logger=False JUST FOR DEMO to
    # showcase style changes.

    uberlogging.configure(cache_structlog_loggers=False)
    logger.info("Plain text, autoconfigured with defaults", text="foo", i=1)
    logging.getLogger("STDLIB").warn("Stdlib logger comming through")

    uberlogging.configure(style=uberlogging.Style.text_color, cache_structlog_loggers=False)
    logger.info("Plain text, colors (forced)", text="foo", i=1)

    uberlogging.configure(style=uberlogging.Style.text_no_color, cache_structlog_loggers=False)
    logger.info("Plain text, no colors", text="foo", i=1)

    uberlogging.configure(style=uberlogging.Style.json, cache_structlog_loggers=False)
    logger.info("Json, no colors", text="foo", i=1)

    dbgl = "dbg"
    logger_confs = {
        dbgl: {
            "level": "DEBUG",
        }
    }
    uberlogging.configure(cache_structlog_loggers=False, logger_confs=logger_confs)
    uberlogging.get_logger(dbgl).debug("This particular logger is in debug level", text="foo", i=1)

    os.environ["UBERLOG_FORCE_TEXT"] = "1"
    uberlogging.configure(cache_structlog_loggers=False)
    logger.info("Autoconfigured with forced text", text="foo", i=1)
    os.environ.unsetenv("UBERLOG_FORCE_TEXT")

    uberlogging.configure(fmt="%(asctime)s %(levelname)s -- %(message)s",
                          datefmt="%H:%M:%S",
                          cache_structlog_loggers=False)
    logger.info("Custom format and timestamp", text="foo", i=1)

    full_conf = {
        "version": 1,
        "formatters": {
            "simple": {
                "format": "<your format goes here> %(message)s",
                "class": "logging.Formatter",
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "simple",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
    uberlogging.configure(full_conf=full_conf, cache_structlog_loggers=False)
    logging.getLogger("FULLCONF").info("Fully custom formatting")


if __name__ == "__main__":
    main()
