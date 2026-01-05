def main():
    print("Hello! I'm Alfred, your personal assistant. How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Alfred: Goodbye!")
            break
        print("Alfred: I'm here to help.")


if __name__ == "__main__":
    main()
