#! /usr/bin/python

""" Decorator print_timer and it's helper functions to print ellapsed time of a function call in the console."""

__author__ = "Paul Duveage, Sweco Nederland B.V."
__copyright__ = "Copyright 2022"
__license__ = "MIT"

import datetime
import functools


def print_timer(
    start_message: str = "", end_message: str = "", show_times: bool = False
):
    """
    Decorator to print ellapsed time of a function call.
    @param start_message:   The message to show when the timer starts.
    @param end_message:     The message to show when the function is completed and timer stops.
    @param show_times:      Display the actual current times.
    @return:
    """

    def decorator_log_timer(func):
        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            print(
                __message_with_time(start_message)
                if show_times
                else start_message
                if start_message
                else ""
            )
            start_time = datetime.datetime.now()
            value = func(*args, **kwargs)
            end_time = datetime.datetime.now()
            msg_elapsed = __message_elsapsed_time(start_time, end_time)
            if show_times:
                print(__message_with_time(end_message, msg_elapsed))
            else:
                print(f"{end_message} {msg_elapsed}\n" if end_message else msg_elapsed)
            return value

        return wrapper_decorator

    return decorator_log_timer


def __message_elsapsed_time(start: datetime.datetime, end: datetime.datetime):
    run_time = end - start
    return f"---- Elapsed time: {run_time.total_seconds():.2f} seconds\n"


def __message_with_time(message, msg_elapsed="\n"):
    return f"{message} @ {datetime.datetime.now().strftime('%H:%M:%S, %d-%m-%Y')} {msg_elapsed}"
