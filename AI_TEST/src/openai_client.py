# openai_client.py
import os
import yaml
from typing import Dict, Any
import openai
import logging

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, config_path: str):
        self.load_config(config_path)
        self.setup_api()

    def load_config(self, config_path: str):
        """Load OpenAI configuration."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.config = config['openai']

    def setup_api(self):
        """Setup OpenAI API with key from environment."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        openai.api_key = api_key

    async def get_completion(self, role: str, prompt: str) -> str:
        """Get completion from OpenAI API."""
        try:
            model = self.config['models'][role]
            params = self.config['parameters'][role]

            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a {role} agent."},
                    {"role": "user", "content": prompt}
                ],
                **params
            )
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error getting completion from OpenAI: {str(e)}")
            raise