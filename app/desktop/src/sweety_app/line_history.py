"""Read-only remote history conversion. All content stays in process memory."""
from .okline_store import message_content
from .okline_errors import LineHistoryError


def parse_history(value):
    if isinstance(value,dict):
        for key in ('messages','result'):
            if key in value:
                return parse_history(value[key])
    if not isinstance(value,list) or any(not isinstance(m,dict) or not m.get('id') for m in value):
        raise LineHistoryError('history_shape_invalid')
    return value


def read_history(api, target, account, limit, exclude_ids, before, decode, allowed):
    if not 4 <= limit <= 30:
        raise LineHistoryError('history_limit_out_of_range')
    found={};visited=set()
    page=parse_history(api.get_recent_messages(target['line_mid'],50))
    for _ in range(10):
        if not allowed():
            raise LineHistoryError('history_cancelled')
        if not page:
            break
        for raw in page:
            stamp=int(raw.get('createdTime') or 0)
            if not stamp:
                raise LineHistoryError('history_timestamp_missing')
            mid=str(raw['id'])
            if mid in exclude_ids or stamp>=before:
                continue
            if int(raw.get('contentType') or 0)==6 or (raw.get('contentMetadata') or {}).get('CALLTYPE'):
                continue
            message=decode(raw)
            if not isinstance(message,dict) or (raw.get('chunks') and not isinstance(message.get('text'),str) and int(message.get('contentType') or 0)==0):
                raise LineHistoryError('history_decryption_failed')
            content=message_content(message)
            if not content:
                continue
            own=message.get('from')==account
            if target.get('line_kind')=='group' and not own:
                content=f"[{message.get('from','?')}] {content}"
            found[mid]=(stamp,{'role':'assistant' if own else 'scammer','content':content})
        if len(found)>=limit:
            break
        oldest=min(page,key=lambda m:(int(m.get('createdTime') or 0),str(m['id'])))
        cursor=str(oldest['id'])
        if cursor in visited:
            raise LineHistoryError('history_pagination_stalled')
        visited.add(cursor)
        if not allowed():
            raise LineHistoryError('history_cancelled')
        page=parse_history(api.get_previous_messages(target['line_mid'],end_message_id=cursor,
            delivered_time=int(oldest.get('deliveredTime') or oldest['createdTime']),count=50))
    else:
        raise LineHistoryError('history_page_limit')
    if not allowed():
        raise LineHistoryError('history_cancelled')
    return [item[1] for _,item in sorted(found.items(),key=lambda pair:(pair[1][0],pair[0]))[-limit:]]
