import os
import requests
from typing import Optional, List, Dict, Generator

ASSISTANT_NAME = "Alfred"


class GeminiAssistant:
    """Gemini-compatible assistant with conversation history and simple streaming.

    - `conversation` keeps a list of turns: dicts with `role` and `content`.
    - `system_prompt` is prepended to each request when present.
    - `process_text(..., stream=True)` yields chunks for a streaming UI.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "text-bison-001", base_url: str = "https://generativelanguage.googleapis.com/v1beta2"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.conversation: List[Dict[str, str]] = []
        self.system_prompt: Optional[str] = None

    def reset_conversation(self) -> None:
        self.conversation = []

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def _build_prompt(self, user_text: str) -> str:
        parts: List[str] = []
        if self.system_prompt:
            parts.append(f"System: {self.system_prompt}")
        for turn in self.conversation:
            parts.append(f"{turn['role'].capitalize()}: {turn['content']}")
        parts.append(f"User: {user_text}")
        return "\n".join(parts)

    def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 256) -> str:
        """Synchronous generation. Uses API when `GOOGLE_API_KEY` is present, otherwise fallback."""
        if not self.api_key:
            return f"[local-fallback] Echo: {prompt}"

        url = f"{self.base_url}/models/{self.model}:generate"
        params = {"key": self.api_key}
        payload = {
            "prompt": {"text": prompt},
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }

        resp = self.session.post(url, params=params, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Parse common response shapes.
        if isinstance(data, dict):
            if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                first = data["candidates"][0]
                if isinstance(first, dict) and "output" in first:
                    return first["output"]
                if isinstance(first, dict) and "content" in first:
                    return first["content"]
            out = data.get("output")
            if isinstance(out, list):
                parts = []
                for item in out:
                    if isinstance(item, dict) and "content" in item:
                        parts.append(item["content"])
                if parts:
                    return "\n".join(parts)

        return str(data)

    def generate_stream(self, prompt: str, chunk_size: int = 60) -> Generator[str, None, None]:
        """Simple, client-side streaming helper.

        - If no API key is present, yields the fallback text in chunks.
        - When using the real API, this helper currently calls `generate` then yields chunks.
          (Adapt to real streaming API if/when needed.)
        """
        full = self.generate(prompt)
        # yield in small chunks to simulate streaming UI
        for i in range(0, len(full), chunk_size):
            yield full[i : i + chunk_size]

    def process_text(self, text: str, stream: bool = False) -> Optional[Generator[str, None, None]]:
        """Process user text, update conversation, and either return a reply string or a generator when `stream=True`.

        - If `stream` is True, returns a generator which yields strings (chunks).
        - If `stream` is False, returns the reply string.
        """
        prompt = self._build_prompt(text)
        if stream:
            gen = self.generate_stream(prompt)
            # append an empty assistant turn now; caller can collect the chunks and update
            self.conversation.append({"role": "assistant", "content": ""})
            return gen

        reply = self.generate(prompt)
        self.conversation.append({"role": "user", "content": text})
        self.conversation.append({"role": "assistant", "content": reply})
        return reply


if __name__ == "__main__":
    import sys

    assistant = GeminiAssistant()

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print(f"{ASSISTANT_NAME}:", assistant.process_text("Say hello in a friendly tone."))
        raise SystemExit(0)
    print(f"Interactive {ASSISTANT_NAME} assistant. Type 'exit' or 'quit' to stop.")
    try:
        while True:
            user = input("You: ")
            if user.strip().lower() in ("exit", "quit"):
                print(f"{ASSISTANT_NAME}: Goodbye")
                break
            reply = assistant.process_text(user)
            print(f"{ASSISTANT_NAME}:", reply)
    except (KeyboardInterrupt, EOFError):
        print("\nAlfred: Goodbye")
