"""Experimental OpenRouter reference-image editing. Does not guarantee strict mask preservation."""
from __future__ import annotations
import base64
import io
import requests
from PIL import Image

ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
DEFAULT_MODEL = 'google/gemini-2.5-flash-image'


def image_data_url(image: Image.Image) -> str:
    stream = io.BytesIO()
    image.convert('RGB').save(stream, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')


def _decode_image_url(value: str) -> Image.Image:
    if not value.startswith('data:image/') or ';base64,' not in value:
        raise ValueError('Model returned a non-inline image URL. This lab currently supports base64 image responses only.')
    data = base64.b64decode(value.split(';base64,',1)[1])
    return Image.open(io.BytesIO(data)).convert('RGB')


def _extract_image(message: dict) -> Image.Image:
    for entry in message.get('images') or []:
        if isinstance(entry, dict):
            url = (entry.get('image_url') or {})
            if isinstance(url, dict):
                url = url.get('url')
            if isinstance(url, str):
                return _decode_image_url(url)
    content = message.get('content')
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            image_url = part.get('image_url') or part.get('url')
            if isinstance(image_url, dict):
                image_url = image_url.get('url')
            if isinstance(image_url, str) and image_url.startswith('data:image/'):
                return _decode_image_url(image_url)
    raise RuntimeError('OpenRouter returned no supported image payload. The model may not support image output or the response format may have changed.')


def edit_image(api_key: str, original: Image.Image, mask: Image.Image, model: str = DEFAULT_MODEL, timeout: int = 180) -> Image.Image:
    if not api_key or not api_key.strip():
        raise ValueError('OpenRouter API key is missing.')
    prompt = (
        'Edit the FIRST reference image, which is an existing graphic design slide. '
        'Remove ALL typography, letters, numbers, captions, words and text overlays. '
        'Reconstruct the underlying visual background naturally. Preserve the EXACT original '
        'composition, subjects, faces, objects, scenery, palette, lighting, shapes, and image dimensions. '
        'Do not add new content or any text. The SECOND reference image is a black-and-white guide: '
        'white means likely text to remove, black means preserve. It is an approximate guide, not a perfect mask; '
        'also remove any text that the guide missed. Preserve all non-text elements, including people and logos '
        'that are pictorial rather than lettering. Return the edited image.'
    )
    payload = {
        'model': model.strip(),
        'modalities': ['image', 'text'],
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': image_data_url(original)}},
            {'type': 'image_url', 'image_url': {'url': image_data_url(mask.convert('RGB'))}},
        ]}],
    }
    try:
        response = requests.post(ENDPOINT, headers={
            'Authorization': f'Bearer {api_key.strip()}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/',
            'X-Title': 'Background Extraction Lab',
        }, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f'OpenRouter network error: {exc}') from exc
    if not response.ok:
        try:
            detail = response.json().get('error', {}).get('message', response.text[:400])
        except ValueError:
            detail = response.text[:400]
        raise RuntimeError(f'OpenRouter HTTP {response.status_code}: {detail}')
    try:
        data = response.json()
        message = data['choices'][0]['message']
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError('Unexpected OpenRouter response structure.') from exc
    return _extract_image(message)
