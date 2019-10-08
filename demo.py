import logging
import os
import sys
from contextvars import Context, ContextVar, copy_context

import structlog
import uberlogging


def main():
    logger = structlog.get_logger()

    # NOTE: using cache_structlog_logger=False JUST FOR DEMO to showcase style changes.

    uberlogging.configure(cache_structlog_loggers=False)
    logger.info("Plain text, autoconfigured with %s", "defaults", text="foo", i=1)
    logging.getLogger("STDLIB").warning("Stdlib logger comming %s", "through")
    logging.getLogger().debug("You should not see this line since root log level is INFO by default")

    uberlogging.configure(style=uberlogging.Style.text_color, cache_structlog_loggers=False)
    logger.info("Plain text, colors (forced)", text="foo", i=1)

    uberlogging.configure(style=uberlogging.Style.text_no_color, cache_structlog_loggers=False)
    logger.info("Plain text, no colors", text="foo", i=1)

    uberlogging.configure(style=uberlogging.Style.json, cache_structlog_loggers=False)
    logger.info("Json, no colors", text="foo", i=1)

    dbgl = "dbg"
    logger_confs = {dbgl: {"level": "DEBUG"}}
    uberlogging.configure(cache_structlog_loggers=False, logger_confs=logger_confs)
    structlog.get_logger(dbgl).debug("This particular logger is in debug level", text="foo", i=1)

    lname = "parent.child"
    logger_confs_list = [dict(
        name=lname,
        level="DEBUG",
    )]
    uberlogging.configure(cache_structlog_loggers=False, logger_confs_list=logger_confs_list)
    structlog.get_logger(lname).debug("Hierarchial logger config through list")

    for suff in ["", "_COLOR", "_NO_COLOR"]:
        env = "UBERLOGGING_FORCE_TEXT" + suff
        os.environ[env] = "1"
        uberlogging.configure(cache_structlog_loggers=False)
        logger.info(f"Autoconfigured with {env}", text="foo", i=1)
        del os.environ[env]

    os.environ["UBERLOGGING_MESSAGE_FORMAT"] = "{asctime} {levelname} -> {message} | context: {context}"
    uberlogging.configure(cache_structlog_loggers=False)
    logger.info(f"Format overriden through environment variable", text="foo", i=1)
    del os.environ["UBERLOGGING_MESSAGE_FORMAT"]

    uberlogging.configure(fmt="{asctime} {levelname} -- {message}",
                          datefmt="%H:%M:%S",
                          cache_structlog_loggers=False)
    logger.info("Custom format and timestamp", text="foo", i=1)

    class MyStream():
        def write(self, s):
            sys.stderr.write("[CUSTOM STREAM] ")
            sys.stderr.write(s)
    uberlogging.configure(stream=MyStream(), style=uberlogging.Style.text_auto,
                          cache_structlog_loggers=False)
    structlog.get_logger().info("Logging with custom stream", text="foo", i=1)

    # Contextvars demo
    ctxvar: ContextVar[str] = ContextVar("request_id")
    uberlogging.configure(contextvars=(ctxvar,), cache_structlog_loggers=False)
    logger.info("Main context - no contextvar value is set")

    def _process_request():
        ctxvar.set("CoqIqNGc3BW")
        logger.info("Child context handling request", payload="bar")
        logger.info("Child context finishing request")
        uberlogging.configure(contextvars=(ctxvar,),
                              style=uberlogging.Style.json, cache_structlog_loggers=False)
        print("ctxvar value", ctxvar.get())
        logger.info("Child context finishing request (JSON mode)")

    ctx: Context = copy_context()
    ctx.run(_process_request)

    logger.info("Main context finished - no contextvar value is set")


if __name__ == "__main__":
    main()
