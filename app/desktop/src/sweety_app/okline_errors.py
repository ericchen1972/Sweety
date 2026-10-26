class SendNotStarted(ValueError):
    """Transport gate declined before any SDK send; safe to defer delivery."""


class LineHistoryError(ValueError):
    """Remote context could not be read safely; do not generate a reply."""


def login_error_details(exc):
    """Keep the traceback and SDK diagnostic fields, without dumping session data."""
    import traceback
    parts=[''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)).strip()]
    seen=set()
    current=exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        fields=[]
        for name in ('code','reason','status','path'):
            value=getattr(current,name,None)
            if value is not None:
                fields.append(f'{name}={value}')
        if fields:
            parts.append(type(current).__name__+': '+', '.join(fields))
        current=current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return '\n'.join(parts)
