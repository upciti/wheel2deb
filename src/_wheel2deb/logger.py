#  Copyright (c) 2015-2018 Cisco Systems, Inc.
#  Copyright (c) 2019 Parkoview SA
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

import sys
import colorama
import logging
from logging import ERROR, WARNING

colorama.init(autoreset=True)

SUMMARY = 100
TASK = 101


class LogFilter(object):
    """
    A custom log filter which excludes log messages above the logged
    level.
    """

    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):  # pragma: no cover
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        return logRecord.levelno <= self.__level


class CustomLogger(logging.getLoggerClass()):
    """
    A custom logging class which adds additional methods to the logger.
    These methods serve as syntactic sugar for formatting log messages.
    """

    def __init__(self, name, level=logging.NOTSET):
        super(logging.getLoggerClass(), self).__init__(name, level)
        logging.addLevelName(SUMMARY, "SUCCESS")
        logging.addLevelName(TASK, "TASK")

    def summary(self, msg, *args, **kwargs):
        if self.isEnabledFor(SUMMARY):
            self._log(SUMMARY, msg, args, **kwargs)

    def task(self, msg, *args, **kwargs):
        if self.isEnabledFor(TASK):
            self._log(TASK, msg, args, **kwargs)


class CounterStreamHandler(logging.StreamHandler):
    """
    A StreamHandler which stores a call counter for each level
    Not thread-safe !
    """

    counters = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record):
        level = record.levelno
        if level not in self.counters:
            self.counters[level] = 0
        self.counters[level] += 1
        super().emit(record)


class TrailingNewlineFormatter(logging.Formatter):
    """
    A custom logging formatter which removes additional newlines from messages.
    """

    def format(self, record):
        if record.msg:
            record.msg = record.msg.rstrip()
        return super(TrailingNewlineFormatter, self).format(record)


class MultilineFormatter(logging.Formatter):
    """
    A custom logging formatter which formats every line in the record
    """

    def format(self, record):
        message = record.msg
        output = ""
        for line in message.splitlines():
            record.msg = line
            output += super().format(record) + "\n"
        record.msg = message
        record.message = output
        return output[:-2]


def get_warning_counter():
    if WARNING in CounterStreamHandler.counters:
        return CounterStreamHandler.counters[WARNING]
    else:
        return 0


def get_error_counter():
    if ERROR in CounterStreamHandler.counters:
        return CounterStreamHandler.counters[ERROR]
    else:
        return 0


def getLogger(name=None):
    """
    Build a logger with the given name and returns the logger.

    :param name: The name for the logger. This is usually the module
                 name, ``__name__``.
    :return: logger object
    """
    logging.setLoggerClass(CustomLogger)

    logger = logging.getLogger(name)
    logger.setLevel(logging.NOTSET)

    logger.addHandler(_get_debug_handler())
    logger.addHandler(_get_info_handler())
    logger.addHandler(_get_task_handler())
    logger.addHandler(_get_warn_handler())
    logger.addHandler(_get_error_handler())
    logger.addHandler(_get_critical_handler())
    logger.addHandler(_get_summary_handler())
    logger.propagate = False

    return logger


def _get_debug_handler():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(MultilineFormatter(dim_text("     %(message)s")))
    handler.setLevel(logging.DEBUG)
    handler.addFilter(LogFilter(logging.DEBUG))

    return handler


def _get_info_handler():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TrailingNewlineFormatter("     %(message)s"))
    handler.setLevel(logging.INFO)
    handler.addFilter(LogFilter(logging.INFO))

    return handler


def _get_task_handler():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(TASK)
    handler.addFilter(LogFilter(TASK))
    handler.setFormatter(
        TrailingNewlineFormatter(" --> {}".format(cyan_text("%(message)s")))
    )

    return handler


def _get_warn_handler():
    handler = CounterStreamHandler(sys.stdout)
    handler.setLevel(logging.WARN)
    handler.addFilter(LogFilter(logging.WARN))
    handler.setFormatter(TrailingNewlineFormatter(yellow_text("     %(message)s")))

    return handler


def _get_error_handler():
    handler = CounterStreamHandler(sys.stderr)
    handler.setLevel(logging.ERROR)
    handler.addFilter(LogFilter(logging.ERROR))
    handler.setFormatter(TrailingNewlineFormatter(red_text("     %(message)s")))

    return handler


def _get_critical_handler():
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.CRITICAL)
    handler.addFilter(LogFilter(logging.CRITICAL))
    handler.setFormatter(TrailingNewlineFormatter(red_text("%(message)s")))

    return handler


def _get_summary_handler():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(SUMMARY)
    handler.addFilter(LogFilter(SUMMARY))
    handler.setFormatter(TrailingNewlineFormatter(green_text("     %(message)s")))

    return handler


def dim_text(msg):
    return color_text(colorama.Style.DIM, msg)


def red_text(msg):
    return color_text(colorama.Fore.RED, msg)


def yellow_text(msg):
    return color_text(colorama.Fore.YELLOW, msg)


def green_text(msg):
    return color_text(colorama.Fore.GREEN, msg)


def cyan_text(msg):
    return color_text(colorama.Fore.CYAN, msg)


def color_text(color, msg):
    return "{}{}{}".format(color, msg, colorama.Style.RESET_ALL)
