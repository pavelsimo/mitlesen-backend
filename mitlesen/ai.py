import os
from typing import Iterator, Optional, Type, TypeVar, Generic, Any
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel
from .prompts import get_system_instruction

load_dotenv()

BACKEND = 'gemini' # openai, gemini

T = TypeVar('T', bound=BaseModel)


class BaseAIClient:
    """Base class for AI clients with shared initialization and configuration logic."""
    
    def __init__(
        self,
        backend: str,
        language: str = 'de',
        model_openai: str = "gpt-4o-mini",
        model_gemini: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None,
    ):
        self.model_openai = model_openai
        self.model_gemini = model_gemini
        self.backend = backend.lower()
        self.system_prompt = system_prompt or get_system_instruction(language)
        self.client = None
        
        self._setup_backend()
    
    def _setup_backend(self):
        """Setup the appropriate backend client."""
        if self.backend == "openai":
            self._setup_openai()
        elif self.backend == "gemini":
            self._setup_gemini()
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def _setup_openai(self):
        """Setup OpenAI client and configuration."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = self.model_openai
        self._messages = [{"role": "system", "content": self.system_prompt}]
    
    def _setup_gemini(self):
        """Setup Gemini client and configuration."""
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.model = self.model_gemini
    
    def _get_openai_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return api_key
    
    def _get_gemini_api_key(self) -> str:
        """Get Gemini API key from environment."""
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            raise ValueError("GEMINI_KEY environment variable not set")
        return api_key


class CompletionClient(BaseAIClient):
    def __init__(
        self,
        backend: str,
        language: str = 'de',
        model_openai: str = "gpt-4o-mini",
        model_gemini: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None,
    ):
        # Use parent class initialization
        super().__init__(backend, language, model_openai, model_gemini, system_prompt)

    def reset(self):
        """Clear conversation history (but keep the system instruction)."""
        if self.backend == "openai":
            self._messages = [{"role": "system", "content": self.system_prompt}]

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


class CompletionStreamClient(BaseAIClient):
    def __init__(
        self,
        backend: str,
        language: str = 'de',
        page_size: int = 10,
        model_openai: str = "gpt-4o-mini",
        model_gemini: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None,
    ):
        # Use parent class initialization
        super().__init__(backend, language, model_openai, model_gemini, system_prompt)
        
        # Stream-specific initialization
        self.page_size = page_size
        self.openai_client: Optional[OpenAI] = None
        self.gemini_chat = None
        self._page = 0
        
        # Setup stream-specific clients
        self._setup_stream_clients()
    
    def _setup_stream_clients(self):
        """Setup stream-specific client configurations."""
        if self.backend == "openai":
            self.openai_client = self.client  # Reuse the client from parent
        elif self.backend == "gemini":
            # For streaming, we need a chat session
            self.gemini_chat = self.client.chats.create(model=self.model_gemini)

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

def get_ai_client(backend: str, **kwargs) -> CompletionClient:
    """Get an AI client for the specified backend (openai or gemini)."""
    return CompletionClient(backend=backend, **kwargs)
