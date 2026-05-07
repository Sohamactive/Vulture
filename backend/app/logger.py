import logging


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger for the given module.

    Deliberately does NOT call logging.basicConfig — configuration
    is the responsibility of the application entry point (e.g. main.py).
    This keeps the library safe for import without side-effects.
    """
    return logging.getLogger(name)
