def main():
    print("Hello! I'm your personal butler. How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Butler: Goodbye!")
            break
        print("Butler: I'm here to help.")


if __name__ == "__main__":
    main()
