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

Notes
- The script uses `GOOGLE_API_KEY` and the Generative Language REST endpoint `https://generativelanguage.googleapis.com/v1beta2`.
- If you do not set an API key the module will use a local fallback reply so you can test the UI and integration.
- Adjust `model` in `GeminiAssistant(...)` if you need a different model name.
