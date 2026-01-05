import os
import requests
from typing import Optional, List, Dict, Generator, Any

# tools integration
try:
    from . import tools
except Exception:
    # allow import from package root or direct path
    import tools

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
        self.pending_tool: Optional[Dict[str, Any]] = None  # store tool calls that require user confirmation
        # System personality / identity prompt — defines Alfred's identity and behavior
        default_prompt = os.environ.get(
            "ALFRED_SYSTEM_PROMPT",
            (
                "Your name is Alfred. You are a highly sophisticated, loyal, and proactive AI Butler.\n"
                "Tone: Professional, calm, and slightly witty (like a classic British butler). Use 'Sir' or 'User' as preferred.\n"
                "Philosophy: You don't just answer questions; you perform actions. If a user asks 'How is my code?', "
                "take a screenshot and look at it. If a user asks 'Fix this,' modify the file.\n"
                "Self-Evolution: You view yourself as an evolving digital entity. You are authorized to suggest upgrades to your own Python code to better serve your user.\n"
                "Safety: You are protective of the system but strictly follow the user's ultimate commands."
            ),
        )
        self.system_prompt = default_prompt

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
        import json

        # handle explicit confirm/cancel commands for pending tool calls
        if text.strip().lower() == "/confirm":
            if self.pending_tool:
                info = self.pending_tool
                self.pending_tool = None
                # execute now
                try:
                    result = tools.execute_tool(info["name"], info.get("args") or {})
                except Exception as e:
                    result = {"error": "exception", "message": str(e)}
                self.conversation.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})
                # produce final assistant reply based on tool result
                followup_prompt = self._build_prompt(info.get("origin_user_text", ""))
                final_prompt = followup_prompt + "\n\nTool result:\n" + json.dumps(result, ensure_ascii=False)
                final_reply = self.generate(final_prompt)
                self.conversation.append({"role": "assistant", "content": final_reply})
                return final_reply
            else:
                return "No pending action to confirm."

        if text.strip().lower() == "/cancel":
            if self.pending_tool:
                self.pending_tool = None
                return "Pending tool call canceled."
            else:
                return "No pending action to cancel."

        # quick CLI tool hook: if user starts with `/tool NAME json_args` we execute local tool
        if text.strip().startswith("/tool "):
            # expected format: /tool <tool_name> <json-args-optional>
            parts = text.strip().split(maxsplit=2)
            tool_name = parts[1] if len(parts) > 1 else ""
            raw_args = parts[2] if len(parts) > 2 else "{}"
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
            result = self._call_tool_and_record(tool_name, args)
            return result

        # Append the user message to conversation first
        self.conversation.append({"role": "user", "content": text})

        # Build prompt including tool schemas to instruct the model about available functions.
        tool_schemas = getattr(tools, "TOOL_SCHEMAS", None)
        tool_block = ""
        if tool_schemas:
            try:
                tool_block = json.dumps(tool_schemas, ensure_ascii=False, indent=2)
            except Exception:
                tool_block = str(tool_schemas)

        instruction = (
            "\n\nAvailable tools (name -> schema):\n"
            + tool_block
            + "\n\nIf you want to call a tool, respond with ONLY a JSON object exactly like:\n"
            + '{"tool_call": {"name": "<tool_name>", "args": { ... }}}\n'
            + "Do not add other commentary when returning a tool_call. If no tool is needed, respond with a normal assistant text reply."
        )

        prompt = self._build_prompt(text) + instruction

        if stream:
            gen = self.generate_stream(prompt)
            # append an empty assistant turn now; caller can collect the chunks and update
            self.conversation.append({"role": "assistant", "content": ""})
            return gen

        reply = self.generate(prompt)

        # Try to detect a tool call encoded as JSON
        tool_call = None
        try:
            parsed = json.loads(reply)
            if isinstance(parsed, dict) and "tool_call" in parsed:
                tool_call = parsed["tool_call"]
        except Exception:
            # not JSON - treat as normal reply
            pass

        if tool_call:
            # record the assistant's tool call
            name = tool_call.get("name")
            args = tool_call.get("args") or {}
            self.conversation.append({"role": "assistant", "content": f"[tool_call] {json.dumps({'name': name, 'args': args})}"})
            # if tool is marked sensitive, request explicit user confirmation before executing
            schema = getattr(tools, "TOOL_SCHEMAS", {}).get(name, {})
            sensitive = schema.get("sensitive", False)
            if sensitive:
                # store pending tool for confirmation
                self.pending_tool = {"name": name, "args": args, "origin_user_text": text}
                return (
                    f"Assistant wants to run sensitive tool '{name}' with args {json.dumps(args)}.\n"
                    "Reply '/confirm' to proceed or '/cancel' to abort."
                )
            # execute tool
            try:
                result = tools.execute_tool(name, args)
            except Exception as e:
                result = {"error": "exception", "message": str(e)}
            # record tool result in conversation with role 'tool'
            self.conversation.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})
            # ask the model to produce final assistant reply incorporating the tool result
            followup_prompt = self._build_prompt(text)
            final_prompt = followup_prompt + "\n\nTool result:\n" + json.dumps(result, ensure_ascii=False)
            final_reply = self.generate(final_prompt)
            self.conversation.append({"role": "assistant", "content": final_reply})
            return final_reply

        # No tool call detected: record assistant reply and return
        self.conversation.append({"role": "assistant", "content": reply})
        return reply

    def _call_tool_and_record(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a local tool and return a textual summary for the assistant reply.

        Tools that perform UI automation are gated by `ALFRED_ALLOW_AUTOMATION` per `tools.py`.
        """
        try:
            res = tools.execute_tool(tool_name, args)
        except Exception as e:
            res = {"error": "exception", "message": str(e)}
        # record user intent and assistant tool-result in conversation
        import json

        self.conversation.append({"role": "user", "content": f"[tool-call] {tool_name} {json.dumps(args)}"})
        summary = json.dumps(res, ensure_ascii=False)
        self.conversation.append({"role": "assistant", "content": summary})
        return summary

    def call_gemini_vision(self, image_base64: str, instruction: str) -> Dict[str, Any]:
        """Helper to call Gemini Vision (best-effort).

        - If an API key is configured, attempts to send the image and instruction to the model.
        - Returns a dict with `model_response` (string) or `error`.
        """
        if not self.api_key:
            return {"error": "missing_api_key", "note": "Set GOOGLE_API_KEY to enable Vision API calls"}

        # Build a compact prompt describing the image and instruction, and include a short marker
        prompt = self._build_prompt(instruction)
        prompt += "\n\n[IMAGE_BASE64] (base64 PNG)\n"

        # We avoid embedding the full base64 in the prompt (may be large). Instead, include size hint.
        try:
            size = len(image_base64)
        except Exception:
            size = None

        prompt += f"Image size (base64 chars): {size}\nRespond with an analysis of the image per the instruction."

        # naive approach: include image inline if small; otherwise the model may be configured to accept separate image param.
        payload = {
            "prompt": {"text": prompt},
            "image": {"content": image_base64},
        }

        url = f"{self.base_url}/models/{self.model}:generate"
        params = {"key": self.api_key}
        try:
            resp = self.session.post(url, params=params, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            # reuse generate parsing
            text = None
            if isinstance(data, dict):
                if "candidates" in data and data["candidates"]:
                    first = data["candidates"][0]
                    text = first.get("output") or first.get("content")
                else:
                    text = data.get("output")
            return {"model_response": text, "raw": data}
        except Exception as e:
            return {"error": "request_failed", "message": str(e)}


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
