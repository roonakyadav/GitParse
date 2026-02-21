import asyncio
import logging
import os
from typing import List, Optional
import httpx
from config import GROQ_API_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# Valid Groq models in order of preference (updated for current API)
VALID_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile", 
    "mixtral-8x7b-32768"
]

class GroqClient:
    def __init__(self):
        self.api_keys = self._parse_api_keys()
        self.current_key_index = 0
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = REQUEST_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1.0
        self.available_models = VALID_MODELS.copy()
        
    def _parse_api_keys(self) -> List[str]:
        """Parse comma-separated API keys from environment."""
        keys_str = os.getenv("GROQ_KEYS", "")
        if not keys_str:
            keys_str = GROQ_API_KEY
            
        if not keys_str:
            raise ValueError("No Groq API keys found in environment")
        
        keys = [key.strip() for key in keys_str.split(",") if key.strip()]
        if not keys:
            raise ValueError("No valid Groq API keys found")
        
        logger.info(f"Loaded {len(keys)} Groq API keys")
        return keys
    
    def _get_current_key(self) -> str:
        """Get current API key with rotation."""
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _get_next_key(self) -> str:
        """Get next API key without rotating."""
        return self.api_keys[self.current_key_index]
    
    def _get_model(self, preferred_model: Optional[str] = None) -> str:
        """Get a valid model, falling back if needed."""
        if preferred_model and preferred_model in self.available_models:
            return preferred_model
            
        # Try configured model
        config_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if config_model in self.available_models:
            return config_model
            
        # Fall back to first available model
        return self.available_models[0]
    
    async def _validate_model(self, model: str) -> bool:
        """Check if model is available by making a small test request."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._get_current_key()}"
            }
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Model {model} is available")
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Model {model} not found")
                    return False
                else:
                    logger.warning(f"Model validation failed for {model}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error validating model {model}: {str(e)}")
            return False
    
    async def call_groq(self, prompt: str, model: Optional[str] = None) -> str:
        """Call Groq API with retry logic and key rotation."""
        # Get valid model with fallback
        model = self._get_model(model)
        
        logger.debug(f"ai.client: Calling Groq with model {model}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_current_key()}"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4096
        }
        
        for attempt in range(self.max_retries):
            current_key = None
            try:
                # Get current key for this attempt
                current_key = self._get_current_key()
                headers["Authorization"] = f"Bearer {current_key}"
                
                logger.debug(f"ai.client: Attempt {attempt + 1}/{self.max_retries} with model {model}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    logger.debug(f"ai.client: Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"]
                        logger.debug(f"ai.client: Got response, length: {len(content)}")
                        return content
                    
                    elif response.status_code == 401:
                        # Invalid API key, try next one
                        logger.warning(f"ai.client: Invalid API key, trying next key (attempt {attempt + 1})")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    
                    elif response.status_code == 429:
                        # Rate limited, wait and retry
                        retry_after = int(response.headers.get("retry-after", self.retry_delay))
                        logger.warning(f"ai.client: Rate limited, waiting {retry_after}s (attempt {attempt + 1})")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    elif response.status_code == 404:
                        # Model not found, try fallback model
                        if model != self.available_models[0]:
                            logger.warning(f"ai.client: Model {model} not found, trying fallback")
                            # Remove invalid model and retry with first available
                            if model in self.available_models:
                                self.available_models.remove(model)
                            model = self.available_models[0]
                            payload["model"] = model
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            logger.error(f"ai.client: All models failed")
                            break
                    
                    else:
                        error_msg = f"Groq API error: {response.status_code} - {response.text}"
                        logger.error(f"ai.client: {error_msg}")
                        raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)
            
            except httpx.TimeoutException as e:
                logger.warning(f"ai.client: Request timeout (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
            
            except httpx.HTTPStatusError as e:
                logger.warning(f"ai.client: HTTP error (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
            
            except httpx.RequestError as e:
                logger.warning(f"ai.client: Request error (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
            
            except Exception as e:
                logger.error(f"ai.client: Unexpected error calling Groq (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
        
        raise Exception(f"Failed to call Groq API after {self.max_retries} attempts")

# Global client instance (lazy initialization)
groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        groq_client = GroqClient()
    return groq_client
