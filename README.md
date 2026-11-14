# Background Extraction Lab

Standalone experimental Streamlit app for removing text from inspiration slides while preserving backgrounds. **Not connected to Creator Suite.**

## Files
- `app.py` — Streamlit UI
- `extraction_engine.py` — OCR text boxes, optional manual rectangles, OpenCV inpainting
- `openrouter_editor.py` — experimental OpenRouter image-reference editing
- `requirements.txt` — Python packages
- `packages.txt` — system Tesseract dependency for Streamlit Community Cloud
- `.streamlit/config.toml` — upload limit
- `.gitignore` — excludes secrets

## Deploy to GitHub + Streamlit Community Cloud
1. Create a new GitHub repository (e.g. `background-extraction-lab`).
2. Upload the contents of this folder **to the repository root** (not the ZIP itself).
3. Go to https://share.streamlit.io/, create a new app from your repository and select `app.py` as entrypoint.
4. In Streamlit Cloud's app settings, add this secret:
   ```toml
   OPENROUTER_API_KEY = "YOUR_REAL_KEY"
   ```
   Never commit API keys, `.env` or `.streamlit/secrets.toml`.
5. Restart the app if needed. Upload an image, inspect the OCR mask, and run Local first.
6. For difficult cases, add manual text rectangles or switch to AI-assisted. AI mode incurs OpenRouter charges.

## Local run
Install Tesseract separately (`tesseract-ocr` on Ubuntu), then:
```
python -m pip install -r requirements.txt
streamlit run app.py
```
To use AI mode locally, set `OPENROUTER_API_KEY` as an environment variable or create an ignored `.streamlit/secrets.toml` file.

## Notes and limitations
- The model ID defaults to `google/gemini-2.5-flash-image`; confirm current model availability, supported image output and pricing on OpenRouter before using it. You can change the model ID in the sidebar.
- OpenRouter is called through the Chat Completions endpoint with `modalities: ["image", "text"]` and two reference images: the original and the approximate mask. This is **not** guaranteed masked editing. Some models/providers may not accept this request format.
- Local OCR misses some stylized text; the mask may cover non-text. Add manual rectangles only when necessary.
- Automatic mode is a deliberately conservative **local-only baseline**. It does **not** intelligently choose between AI and local reconstruction yet, and it does not automatically spend credits.
- AI output may modify subjects, composition, or dimensions. Always inspect.
- Uploaded images are sent to OpenRouter only when you explicitly run AI-assisted mode. Do not use sensitive or private photos without appropriate permission.
- No image is saved to disk by the app. Streamlit may retain in-memory state during the session.
- Do not publish extracted copyrighted design assets as your own without appropriate rights.

## Suggested first benchmark
Test the six inspiration slides using Local and AI-assisted, keeping track of: (1) text fully removed, (2) subjects unchanged, (3) background fidelity, (4) layout unchanged, (5) artifacts.
