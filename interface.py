import json
import threading
import os
from pathlib import Path
import flet as ft
from flet import Page, Column, Row, TextField, IconButton, Text, ThemeMode, ScrollMode

from assistant import GeminiAssistant

UI_CONFIG_PATH = Path(os.environ.get("ALFRED_WORKSPACE", Path.cwd())) / "ui_style.json"


def load_ui_config():
    if UI_CONFIG_PATH.exists():
        try:
            return json.loads(UI_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main(page: Page):
    page.title = "Alfred Butler"
    page.window_width = 480
    page.window_height = 120
    page.window_always_on_top = True
    page.bgcolor = "#111111"
    page.theme_mode = ThemeMode.DARK
    page.padding = 8
    page.window_frameless = True

    assistant = GeminiAssistant()

    ui_cfg = load_ui_config()
    bar_color = ui_cfg.get("bar_color", "#111111")
    accent = ui_cfg.get("accent", "#2b8cff")

    # Aura indicator
    aura = ft.Container(width=24, height=24, border_radius=12, bgcolor=accent, opacity=0.0)


    chat_history = Column(expand=True, scroll=ScrollMode.ALWAYS)
    user_input = TextField(hint_text="Command Alfred...", expand=True, border_color="#3d3d3d")

    def send_click(e):
        txt = user_input.value.strip()
        if not txt:
            return
        chat_history.controls.append(Text(f"You: {txt}", color="#ffffff"))
        user_input.value = ""
        page.update()
        # process in thread to avoid blocking UI
        def work():
            try:
                out = assistant.process_text(txt)
                if hasattr(out, '__iter__') and not isinstance(out, str):
                    text = ''.join(list(out))
                else:
                    text = out
            except Exception as e:
                text = f"(error) {e}"
            page.client_storage.set('last_reply', text)
            page.invoke_js('alredAppend', args=[text])

        threading.Thread(target=work, daemon=True).start()

    send_btn = IconButton(ft.icons.SEND, on_click=send_click)

    top = Row([Text("ALFRED", size=12, color="#888888")])

    page.add(Row([aura, top]), chat_history, Row([user_input, send_btn]))

    def pulse_aura():
        # simple pulse animation: increase opacity then fade
        try:
            for v in [0.2, 0.5, 0.8, 0.5, 0.2, 0.0]:
                aura.opacity = v
                page.update()
                import time

                time.sleep(0.12)
        except Exception:
            pass

    # expose for external triggers (e.g., when Vision is used)
    page.client_storage.set('pulse_aura_fn', True)



def run_app():
    ft.app(target=main)


if __name__ == "__main__":
    run_app()
