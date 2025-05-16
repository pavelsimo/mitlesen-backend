import os
from typing import Iterator, Optional, Type, TypeVar, Generic, Any
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

BACKEND = 'gemini' # openai, gemini

T = TypeVar('T', bound=BaseModel)

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
        
        if self.backend == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = model_openai
            self._messages = [{"role": "system", "content": self.system_instruction}]
        elif self.backend == "gemini":
            self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    def reset(self):
        """Clear conversation history (but keep the system instruction)."""
        if self.backend == "openai":
            self._messages = [{"role": "system", "content": self.system_instruction}]

    def complete(self, prompt: str, response_schema: Optional[Type[T]] = None) -> str:
        """
        Send one non-streaming request and get the full reply.
        
        Args:
            prompt: The prompt to send to the model
            response_schema: Optional Pydantic model class that defines the expected response schema
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
            config = {
                'response_mime_type': 'application/json',
            }
            
            if response_schema:
                config['response_schema'] = response_schema
            
            response = self.client.models.generate_content(
                model=self.model_gemini,
                contents=prompt,
                config=config
            )
            
            return response.text


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
                    # 'generation_config': {
                    #     'response_format': {'type': 'json_object'}
                    # }
                }
            ):
                if chunk.text:
                    yield chunk.text
