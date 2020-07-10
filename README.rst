**********************************************
Uberlogging - Python logging the way I like it
**********************************************

.. image:: https://img.shields.io/pypi/v/uberlogging.svg
    :target: https://pypi.python.org/pypi/uberlogging

.. image:: https://img.shields.io/travis/haizaar/uberlogging.svg
        :target: https://travis-ci.org/haizaar/uberlogging

.. image:: https://img.shields.io/pypi/dm/uberlogging.svg
    :target: https://pypi.python.org/pypi/uberlogging

Highly opinionated wrapper/configuration around
`structlog <http://www.structlog.org/en/stable/>`_ and stdlib logger.

Python 3.7+ only. To use contextvar, minimum Python 3.7.1 is required.

Why
###
Every project starts with burden of logging configuration.
We want colors for interactive debugging, plain text in local
dev when redirecting to file, and JSON when running in production
with central log collection system. Finally, I like
`structlog <http://www.structlog.org/en/stable/>`_,
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
.. code:: python

  import uberlogging
  uberlogging.configure()

That's all. You are ready to go. Simply import ``structlog`` or stdlib
``logging``, create your logger and start writing your app.

.. code:: python

  import structlog
  logger = structlog.get_logger("main")
  logger.info("Rocky road", to="Dublin")

Define ``UBERLOGGING_FORCE_TEXT=1`` environment variable
to force text output in non-tty streams. Useful for local environments when
running your app with output redirection.

Formatting
##########
Structlog's context (key/value pairs passed to logging call) is rendered as
``<key1>=<value1> <key2>=<value2>`` (or empty string otherwise) and is
available as ``{context}`` formatting variable. If non empty it will be
4-space padded (yes, it's not generic, but I find it very convenient with
the default configuration).

If you employ contextvars, they will be rendered similarly and available as
``{contextvars}}`` formatting variable. Similarly, it's either single or
4-space padded depending whether exists non-empty structlog context for the
current log record. See dedicated section on contextvars below.

Envrionment overrides
#####################
Sometimes people want things their own way and that's without changing actual code.
To address that uberlogging provides ability to control some of its configuration
though environment variables:

``UBERLOGGING_FORCE_TEXT``
  Define to non-empty value to force textual (not JSON) output. Colouring is autodetected

``UBERLOGGING_FORCE_TEXT_COLOR``
  Same as above, but with with colours always *enabled*

``UBERLOGGING_FORCE_TEXT_NO_COLOR``
  Same as above, but with with colours always *disabled*

``UBERLOGGING_MESSAGE_FORMAT``
  String that overrides logging message format.
  E.g. ``"{asctime} {levelname} {message}``. Note that only "{"
  `styles <https://docs.python.org/3/howto/logging-cookbook.html#formatting-styles>`_
  are supported.

Contextual logging
##################
Structlogs's ``logger.bind(request_id="foo")`` is great for simple things but when you have
multi-layer request handling, passing the same instance of bound logger is a). cumbersome and
b). requires the same logger to be used by everything that handles the request.

I've long missed log4cxx `Nested Diagnostic Contexts <https://logging.apache.org/log4cxx/latest_stable/usage.html#Nested_Diagnostic_Contexts>`_
in Python and now with contextvars we can finally achieve that. The best part is that it
works both in threaded and asyncio code!

If you never heard of contextvars, please read official
`documentation <https://docs.python.org/3/library/contextvars.html>`_. In the nutshell
it "kinda" replaces thread local storage and is natively supported in asyncio, i.e.
it's both thread-safe and concurrent safe.

To employ contextvars in uberlogging you need to:

* Create a contextvar somewhere in your code
* Pass this context var to ``uberlogging.configure()``
* Set contextvar values whenever your like and all subsequent log messages will
  have its value rendered as part of the ``contextvar`` extra section

Here is an example:

.. code-block:: python

  import asyncio
  from contextvars import ContextVar

  import structlog
  import uberlogging

  ctx_request_id: ContextVar = ContextVar("request_id")
  logger = structlog.get_logger(__name__)


  async def handle_request(request_id: str) -> None:
      ctx_request_id.set(request_id)
      logger.info("Handling request")  # Will produce "Handling request    request_id=<request_id>


  async def server():
      logger.info("Main server handling two requests")
      t1 = asyncio.create_task(handle_request("Zf1glE"))
      t2 = asyncio.create_task(handle_request("YcEf73"))
      await asyncio.wait((t1, t2))
      logger.info("Main server done")

  if __name__ == "__main__":
      uberlogging.configure(contextvars=(ctx_request_id,))
      asyncio.run(server())

This code will produce the following::

  2019-10-07T13:41:17.669 __main__        INFO    ## Main server handling two requests   ctx.server:17
  2019-10-07T13:41:17.669 __main__        INFO    ## Handling request    request_id='Zf1glE'    ctx.handle_request:13
  2019-10-07T13:41:17.669 __main__        INFO    ## Handling request    request_id='YcEf73'    ctx.handle_request:13
  2019-10-07T13:41:17.669 __main__        INFO    ## Main server done    ctx.server:21

Note that logger invocations inside the request handler do not mention any ``request_id`` - it's
injected by logging formatter from the context.


Where are tests?
################
No tests, only deadlines :)
Seriously though, there is ``demo.sh`` script that's good enough for now, since
this library is not going to see much of a development.

Development
###########
.. code-block:: shell

  echo 'layout pipenv' > .envrc
  direnv allow  # will take a while
  make bootstrap
