def main():
    from assistant import GeminiAssistant

    assistant = GeminiAssistant()
    print("Hello! I'm Alfred, your personal assistant. Type '/tool name {json}' to run a local tool.\nType 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Alfred: Goodbye!")
            break
        # the assistant knows how to handle `/tool` commands via `process_text`
        try:
            out = assistant.process_text(user_input)
            if hasattr(out, '__iter__') and not isinstance(out, str):
                # stream generator
                for chunk in out:
                    print(chunk, end='', flush=True)
                print()
            else:
                print("Alfred:", out)
        except Exception as e:
            print("Alfred: (error)", str(e))


if __name__ == "__main__":
    main()
