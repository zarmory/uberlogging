**********************************************
Uberlogging - Python logging the way I like it
**********************************************

Highly opinionated wrapper/configuration around
`structlog <http://www.structlog.org/en/stable/>`_.

Why
###
Every project starts with burden of logging configuration.
We want colors for interactive debugging, plain text in local
dev when redirecting to file, and JSON when running in production
with central log collection system. Finally, I like
`structlog <http://www.structlog.org/en/stable/index.html>`_,
but most of the libraries do not use it, so I need to configure
both libraries in compatible way.

This library does exactly that - configures logging as described
above. It does it both for structlog and standard library logging.

Opinionated?
############
Yes it is, since it merely configures great tools written by
other great people to behave the way I personally prefer.

For instance, I prefer *not* to render structlog's key/val
arguments as separate attributes in JSON output, since I find
it much more convenient to read them as part of the text message,
even in centralized logging UIs such as Graylog - processing them
as separate fields will require me to enable million field columns,
since each log message has its own context; and I don't use logs,
but metrics for broader analysis.

Usage
#####
::

  import uberlogging
  uberlogging.configure()

That's all. You are ready to go. Simply import ``structlog`` or standard
library's ``logging``, create your logger and start writing your app.

For convenience, structlog's ``get_logging`` has been hoisted to uberlog::

  logger = uberlogging.get_logger("main")
  logger.info("Here we go")

Define ``UBERLOG_FORCE_TEXT=1`` environment variable
to force text output in non-tty streams. Useful for local environments when
running your app with output redirection.

Where are tests?
################
No tests, only deadlines :)
Seriously though, there is ``demo.sh`` script that's good enough for now, since
this library is not going to see much of a development.

Tested on Python3.6+ only!
