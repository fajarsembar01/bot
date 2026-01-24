"""Entrypoint for Ticketmaster simple bot."""

try:
    from .simple_bot import main
except ImportError:
    try:
        from ticketmaster.simple_bot import main
    except ImportError:
        from simple_bot import main


if __name__ == "__main__":
    main()
