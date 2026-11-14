import io
import os
from PIL import Image, ImageDraw
import streamlit as st
from extraction_engine import ocr_boxes, make_mask, inpaint
from openrouter_editor import edit_image, DEFAULT_MODEL

st.set_page_config(page_title='Background Extraction Lab', page_icon='🖼️', layout='wide')
st.title('Background Extraction Lab')
st.caption('Standalone experiment • Local OCR + OpenCV or OpenRouter image editing • Not connected to Creator Suite')
st.info('AI image editing is experimental. It can change people, objects, layout, and dimensions. Always compare with the original.')

uploaded = st.file_uploader('Upload inspiration slide', type=['png','jpg','jpeg','webp'])
if not uploaded:
    st.stop()
try:
    original = Image.open(uploaded).convert('RGB')
except Exception as exc:
    st.error(f'Could not open image: {exc}')
    st.stop()

with st.sidebar:
    st.header('Settings')
    method = st.radio('Method', ['Local (free)', 'AI-assisted (OpenRouter)', 'Automatic (experimental)'])
    padding = st.slider('OCR mask padding', 0, 25, 5)
    radius = st.slider('Local inpainting radius', 1, 12, 4)
    st.caption('The AI model uses the original slide and a guide mask as reference images. The mask is NOT guaranteed to be enforced pixel-by-pixel.')
    model = st.text_input('OpenRouter image-editing model ID', value=DEFAULT_MODEL)
    st.caption('Model availability, image output and prices can change. Confirm in your OpenRouter dashboard before using credits.')
    key = None
    try:
        key = st.secrets.get('OPENROUTER_API_KEY')
    except Exception:
        pass
    key = key or os.environ.get('OPENROUTER_API_KEY')
    if key:
        st.success('OpenRouter key configured in secrets/environment')
    else:
        st.warning('AI mode requires OPENROUTER_API_KEY in Streamlit Secrets.')

try:
    boxes = ocr_boxes(original)
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.write(f'OCR detected **{len(boxes)} text fragments**. Detection is imperfect, especially for large decorative lettering.')
if boxes:
    with st.expander('OCR detections'):
        st.dataframe(boxes, use_container_width=True)

st.subheader('Optional manual text rectangles')
st.caption('If OCR misses a heading, enter its rectangle as x1,y1,x2,y2 in original-image pixels, one per line. Example: 20,30,240,100. Leave empty for OCR-only.')
rect_text = st.text_area('Extra text rectangles', height=80, placeholder='20,30,240,100')
rects=[]
try:
    for line in rect_text.splitlines():
        if line.strip():
            vals=[int(x.strip()) for x in line.split(',')]
            if len(vals)!=4 or vals[2]<=vals[0] or vals[3]<=vals[1]:
                raise ValueError('Each rectangle must have four numbers and positive width/height.')
            rects.append(tuple(vals))
except ValueError as exc:
    st.error(f'Invalid rectangle: {exc}')
    st.stop()
mask = make_mask(original, boxes, padding, rects)
left,right = st.columns(2)
with left:
    st.image(original, caption=f'Original ({original.width} × {original.height})', use_container_width=True)
with right:
    st.image(mask, caption='Text-removal guide mask (white = remove)', use_container_width=True)

if st.button('Extract background', type='primary'):
    try:
        if method == 'Local (free)':
            cleaned = inpaint(original, mask, radius)
            used = 'Local OpenCV'
        elif method == 'AI-assisted (OpenRouter)':
            if not key:
                st.error('Add OPENROUTER_API_KEY to Streamlit Secrets before running AI mode.')
                st.stop()
            with st.spinner('Sending image to OpenRouter for editing (may incur API charges)...'):
                cleaned = edit_image(key, original, mask, model=model)
            used = 'OpenRouter AI'
        else:
            # Conservative experimental routing: no automatic paid API calls.
            # For complex/missed text, ask for deliberate AI choice instead.
            if not boxes:
                st.warning('OCR detected no text. Automatic mode will not erase image details blindly. Try manual rectangles or AI-assisted mode.')
                st.stop()
            cleaned = inpaint(original, mask, radius)
            used = 'Automatic experimental (local only)'
        st.session_state['result'] = cleaned
        st.session_state['result_source'] = uploaded.name
        st.session_state['result_method'] = used
        st.session_state['result_mask'] = mask
    except Exception as exc:
        st.error(f'Extraction failed: {exc}')

if st.session_state.get('result_source') == uploaded.name and st.session_state.get('result') is not None:
    cleaned = st.session_state['result']
    st.subheader('Result')
    st.write(f'Method: **{st.session_state["result_method"]}**')
    c1,c2=st.columns(2)
    c1.image(original, caption='Original', use_container_width=True)
    c2.image(cleaned, caption=f'Extracted ({cleaned.width} × {cleaned.height})', use_container_width=True)
    if cleaned.size != original.size:
        st.warning('AI returned a different image size. Inspect alignment and subject fidelity before using it.')
    stream=io.BytesIO()
    cleaned.save(stream,format='PNG')
    st.download_button('Download extracted PNG',stream.getvalue(),file_name='extracted_background.png',mime='image/png')
    mask_stream=io.BytesIO()
    st.session_state['result_mask'].save(mask_stream,format='PNG')
    st.download_button('Download text mask',mask_stream.getvalue(),file_name='text_mask.png',mime='image/png')
    st.caption('Check text removal, subject preservation, layout fidelity, and artifacts manually. A successful API call does not mean a successful extraction.')
