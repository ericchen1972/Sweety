class SendNotStarted(ValueError):
    """Transport gate declined before any SDK send; safe to defer delivery."""
