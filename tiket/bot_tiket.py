"""Entrypoint for Tiket.com auto-buy bot."""

try:
    from .auto_buy import main
except ImportError:
    try:
        from tiket.auto_buy import main
    except ImportError:
        from auto_buy import main


if __name__ == "__main__":
    main()
