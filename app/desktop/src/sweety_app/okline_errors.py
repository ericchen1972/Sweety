class SendNotStarted(ValueError):
    """Transport gate declined before any SDK send; safe to defer delivery."""


class LineHistoryError(ValueError):
    """Remote context could not be read safely; do not generate a reply."""
