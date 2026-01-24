"""Backward-compatible entrypoint for the Loket queue bot."""

try:
    from .queue_bot import main
except ImportError:
    try:
        from loket.queue_bot import main
    except ImportError:
        from queue_bot import main


if __name__ == "__main__":
    main()
