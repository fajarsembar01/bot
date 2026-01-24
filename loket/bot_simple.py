"""Backward-compatible entrypoint for the Loket simple bot."""

try:
    from .simple_bot import main
except ImportError:
    try:
        from loket.simple_bot import main
    except ImportError:
        from simple_bot import main


if __name__ == "__main__":
    main()
