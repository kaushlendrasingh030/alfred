# Alfred — Gemini assistant (minimal)

This small example shows how to call the Google Generative Language (Gemini-compatible) REST endpoint and provides a tiny interactive assistant.

Usage

- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

- Set your API key (optional — a local fallback will run if not set):

Windows PowerShell:
```powershell
$env:GOOGLE_API_KEY = 'YOUR_API_KEY'
```

- Run interactive assistant:

```bash
python assistant.py
```

- Quick demo (prints a short reply):

```bash
python assistant.py --demo
```

Web UI
------
Start the FastAPI web app (requires packages in `requirements.txt`):

```powershell
cd T:\sara\alfred
& T:\sara\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

Desktop UI (Flet)
------------------
Start the lightweight desktop UI (floating bar) with Flet:

```powershell
cd T:\sara\alfred
& T:\sara\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python interface.py
```

To package Alfred as a standalone app (Windows exe):

```powershell
pip install pyinstaller flet
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" interface.py
```

Notes on safety:
- Enable UI automation with `ALFRED_ALLOW_AUTOMATION=1`.
- Enable code self-modification with `ALFRED_ALLOW_SELF_MODIFY=1` and always review proposed changes.

Notes
- The script uses `GOOGLE_API_KEY` and the Generative Language REST endpoint `https://generativelanguage.googleapis.com/v1beta2`.
- If you do not set an API key the module will use a local fallback reply so you can test the UI and integration.
- Adjust `model` in `GeminiAssistant(...)` if you need a different model name.
