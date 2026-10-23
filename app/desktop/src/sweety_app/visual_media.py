"""Bounded in-memory LINE visual inputs. No screenshot, OCR or native permissions."""
import base64
from io import BytesIO
import re
import warnings

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_MEDIA_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 30_000_000
MAX_EDGE = 1536


class MediaError(RuntimeError):
    pass


def check_media_size(size):
    try:
        if int(size or 0) > MAX_MEDIA_BYTES:
            raise MediaError('media_too_large')
    except (ValueError, TypeError) as exc:
        raise MediaError('media_size_invalid') from exc


def sticker_urls(message):
    meta = message.get('contentMetadata') or {}
    sticker_id = str(meta.get('STKID') or '')
    if not re.fullmatch(r'[0-9]{1,20}', sticker_id):
        raise MediaError('sticker_id_invalid')
    from okline.endpoints import CDN_STICKER_BASE
    base = CDN_STICKER_BASE + '/stickershop/v1/sticker/' + sticker_id
    return [base + '/android/sticker.png', base + '/iPhone/sticker_key@2x.png']


def download_sticker(message, *, get=requests.get):
    for url in sticker_urls(message):
        # Fixed LINE CDN paths only; neither redirects nor message URLs are followed.
        with get(url, timeout=(10, 25), stream=True, allow_redirects=False) as response:
            if response.status_code == 404:
                continue
            if response.status_code != 200:
                raise MediaError('sticker_download_failed')
            check_media_size(response.headers.get('Content-Length'))
            chunks=[];size=0
            for chunk in response.iter_content(64 * 1024):
                size += len(chunk)
                check_media_size(size)
                chunks.append(chunk)
            return b''.join(chunks)
    raise MediaError('sticker_preview_unavailable')


def decrypt_image_blob(key, payload):
    from okline.e2ee_crypto import decrypt_blob
    return decrypt_blob(key, payload)


def download_obs_bytes(api, sid, oid, message_id):
    # Preserve the pinned SDK's authentication while bounding the response stream.
    obs = api.obs
    path = f'/r/talk/{sid}/{oid}'
    base = obs._obs_base()
    headers = obs._t.base_headers(with_access=False, base=base)
    headers.update(obs._obs_auth(path))
    headers.pop('content-type', None)
    headers.update(obs._talk_meta_header(None, message_id))
    with obs._t._send('GET', base + path, headers=headers,
                      stream=True, timeout=(10, 25)) as response:
        response.raise_for_status()
        check_media_size(response.headers.get('Content-Length'))
        chunks = []
        size = 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            check_media_size(size)
            chunks.append(chunk)
        return b''.join(chunks)


def download_image(api, message):
    meta = message.get('contentMetadata') or {}
    check_media_size(meta.get('FILE_SIZE'))
    if message.get('chunks'):
        message=api.decrypt_message(message)
        meta=message.get('contentMetadata') or {}
    oid=str(meta.get('OID') or message.get('id') or '')
    sid=str(meta.get('SID') or 'm')
    if not oid or '/' in oid or '/' in sid or '..' in oid or '..' in sid:
        raise MediaError('image_object_invalid')
    # Both clear and decoded Letter-Sealed messages are supported. The SDK's
    # download_sealed_media re-decrypts chunks, so use its blob primitive after decode.
    payload=download_obs_bytes(api, sid, oid, str(message.get('id') or ''))
    check_media_size(len(payload))
    if meta.get('ENC_KM'):
        encoded=str(meta['ENC_KM'])
        try:
            key=base64.b64decode(encoded+'='*(-len(encoded)%4),validate=True)
            payload=decrypt_image_blob(key,payload)
        except Exception as exc:
            raise MediaError('image_decryption_failed') from exc
    return payload


def encode_images(payload):
    if not isinstance(payload, bytes) or not payload:
        raise MediaError('image_unavailable')
    check_media_size(len(payload))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise MediaError('image_pixels_too_large')
                # Multiple representative frames for animated images when present;
                # LINE sticker CDN paths provide a static visual preview.
                count=getattr(source,'n_frames',1)
                frames=sorted(set([0, count//2, count-1])) if count>1 else [0]
                result=[]
                for index in frames:
                    source.seek(index)
                    image=ImageOps.exif_transpose(source.convert('RGBA'))
                    image.thumbnail((MAX_EDGE,MAX_EDGE),Image.Resampling.LANCZOS)
                    canvas=Image.new('RGB',image.size,'white')
                    canvas.paste(image,mask=image.getchannel('A'))
                    output=BytesIO();canvas.save(output,format='JPEG',quality=85)
                    result.append('data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode('ascii'))
                return result
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise MediaError('image_decode_failed') from exc
