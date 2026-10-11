# ComicCraft - AI Comic Story Creator

A Streamlit app that uses Google Gemini to create a five-panel comic story and generate panel illustrations.

## Run in VS Code (Windows)

1. Install Python 3.10 or newer.
2. Open this folder in VS Code and open Terminal.
3. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Open `.env` and replace `YOUR_GEMINI_API_KEY_HERE` with your own Gemini API key.
6. Start the app:
   ```powershell
   streamlit run comic_app.py
   ```
7. Open the local URL shown in the terminal (usually http://localhost:8501).

## Notes
- The main interface is `comic_app.py`.
- `app.py` is the command-line story generator; `ui.py` is an alternate simple interface.
- Backup files are included to match the supplied project folder.
- Never upload a real `.env` file or API key to a public GitHub repository. The `.gitignore` excludes `.env`.
- Image generation requires an API key and access to a compatible Gemini image model. Model availability and quotas depend on your Google AI account.
