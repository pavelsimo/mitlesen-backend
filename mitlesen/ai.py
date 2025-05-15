import os
from typing import Iterator, Optional
from openai import OpenAI
from google import genai
from dotenv import load_dotenv

load_dotenv()

BACKEND = 'gemini' # openai, gemini

class CompletionClient:
    def __init__(
        self,
        backend: str,
        model_openai: str = "gpt-4o-mini",
        model_gemini: str = "gemini-2.0-flash",
        system_instruction: str = "You are a precise language-processing assistant. You will receive a raw transcript from a German video",
    ):
        self.model_openai = model_openai
        self.model_gemini = model_gemini
        self.backend = backend.lower()
        self.system_instruction = system_instruction
        # TODO(Pavel): Gemini models are accessible using the OpenAI libraries
        # https://ai.google.dev/gemini-api/docs/openai
        if self.backend == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = model_openai
            # start with just the system message
            self._messages = [{"role": "system", "content": self.system_instruction}]
        elif self.backend == "gemini":
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            # start a persistent chat session
            self.chat = client.chats.create(model=model_gemini)
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    def reset(self):
        """Clear conversation history (but keep the system instruction)."""
        if self.backend == "openai":
            self._messages = [{"role": "system", "content": self.system_instruction}]
        elif self.backend == "gemini":
            # start a fresh Gemini chat
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            self.chat = client.chats.create(model=self.chat.model)

    def complete(self, prompt: str) -> str:
        """
        Send one non-streaming request and get the full reply.
        Appends the user prompt to history under the hood.
        """
        if self.backend == "openai":
            self._messages.append({"role": "user", "content": prompt})
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content

        else:  # gemini
            # for Gemini, just send into the existing chat session
            chunk = self.chat.send_message(
                prompt,
                config={
                    'response_mime_type': 'application/json',
                    'generation_config': {
                        'response_format': {'type': 'json_object'}
                    }
                }
            )
            return chunk.text


class CompletionStreamClient:
    def __init__(
        self,
        backend: str,
        page_size: int = 10,
        model_openai: str = "gpt-4o-mini",
        model_gemini: str = "gemini-2.0-flash",
        system_instruction: str = "You are a precise language-processing assistant. You will receive a raw transcript from a German video",
    ):
        self.backend = backend
        self.page_size = page_size
        self.openai_client: Optional[OpenAI] = None
        self.gemini_chat = None
        self.system_instruction = system_instruction
        self.model_openai = model_openai
        self.model_gemini = model_gemini

        if backend == "openai":
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self._messages = [{"role": "system", "content": self.system_instruction}]
        elif backend == "gemini":
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            self.gemini_chat = client.chats.create(model=self.model_gemini)

        self._page = 0

    def _make_user_prompt(self, base_query: str) -> str:
        self._page += 1
        offset = (self._page - 1) * self.page_size
        return f"{base_query}\nPlease show results {offset + 1}–{offset + self.page_size}."

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield tokens (OpenAI) or text chunks (Gemini) for the next page."""
        prompt = self._make_user_prompt(prompt)

        if self.backend == "openai":
            # append the new user message
            self._messages.append({"role": "user", "content": prompt})

            # start streaming
            stream = self.openai_client.chat.completions.create(
                model=self.model_openai,
                messages=self._messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        elif self.backend == "gemini":
            for chunk in self.gemini_chat.send_message_stream(
                prompt,
                config={
                    'response_mime_type': 'application/json',
                    'generation_config': {
                        'response_format': {'type': 'json_object'}
                    }
                }
            ):
                if chunk.text:
                    yield chunk.text
