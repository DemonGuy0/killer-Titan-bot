from groq import Groq

class GroqChatSession:
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Always format your responses using Telegram-compatible markdown syntax. Use **text** for bold, *text* for italic, `code` for inline code, ```language\ncode\n``` for code blocks, [text](url) for links, and other standard markdown elements that Telegram supports. Ensure all responses are properly formatted for Telegram messaging."
            }
        ]

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def chat(self) -> str:
        chat_completion = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages
        )
        reply = chat_completion.choices[0].message.content
        self.add_assistant_message(reply)
        return reply

    def reset(self):
        self.messages = []
