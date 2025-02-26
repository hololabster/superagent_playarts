# llm_service.py
from .base_service import BaseService
from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger(__name__)

class LLMService(BaseService):
    """
    Service for handling natural language processing and intent detection
    """

    # Style filter mappings
    FILTER_MAPPING = {
        'ippy': 'useIppy',
        'pepe': 'usePepe',
        'coco': 'useCoco',
        'mfer': 'useMfer',
        'milady': 'useMilady',
        'pepenobi': 'usePepenobi',
        'boop': 'useBoop',
        'monadpepe': 'useMonadpepe',
        'patty': 'usePatty',
        'claude': 'useClaude',
        'bluearbpepe': 'useBlueArbpepe',
        'storymushy': 'useStoryMushy',
        'fate': 'useFate',
        'pipi': 'usePipi',
        'bopr': 'useBopr',
        'sparky': 'useSparky'
    }

    def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Parse user input to determine command type and parameters
        
        Args:
            user_input: Raw user input string
            
        Returns:
            Dictionary containing command type and parameters
        """
        try:
            logger.info(f"Parsing intent for input: {user_input}")
            lower_input = user_input.lower()

            # Check commands in priority order
            intent = (
                self._check_training_intent(lower_input, user_input) or
                self._check_image_generation_intent(lower_input, user_input) or
                self._check_nft_intent(lower_input, user_input) or
                self._check_wallet_intent(lower_input, user_input) or
                self._get_unknown_intent()
            )
            
            logger.debug(f"Detected intent: {intent}")
            return intent

        except Exception as e:
            logger.error(f"Error parsing intent: {str(e)}", exc_info=True)
            return self._get_unknown_intent()

    def get_image_filters(self, prompt: str) -> List[str]:
        """
        Get recommended style filters for image generation
        
        Args:
            prompt: User's image generation prompt
            
        Returns:
            List of applicable style filters
        """
        try:
            filter_prompt = self._create_filter_prompt(prompt)
            response = self.generate_llm_response(filter_prompt)
            
            if not response:
                return []
                
            selected_filter = response.strip().lower()
            mapped_filter = self.FILTER_MAPPING.get(selected_filter)
            
            return [mapped_filter] if mapped_filter else []
            
        except Exception as e:
            logger.error(f"Error getting image filters: {str(e)}", exc_info=True)
            return []

    def _check_training_intent(self, lower_input: str, original_input: str) -> Optional[Dict[str, Any]]:
        training_keywords = [
            'train image', 'train character', 'training character',
            'train lora', 'lora training', 'train my character'
        ]
        if any(k in lower_input for k in training_keywords):
            if "nft" in lower_input:
                return {
                    "command_type": "image_training_nft",
                    "params": {
                        # ...
                    }
                }
            else:
                return {
                    "command_type": "image_training_upload",
                    "params": {
                        # ...
                    }
                }
        return None

    def _check_image_generation_intent(self, lower_input: str, original_input: str) -> Optional[Dict[str, Any]]:
        """Check for image generation intent"""
        image_keywords = ['generate image', 'create image', 'make image', 'draw']
        
        if any(keyword in lower_input for keyword in image_keywords):
            prompt = self._extract_generation_prompt(lower_input, image_keywords)
            selected_filters = self.get_image_filters(prompt)
            
            filter_params = {
                filter_name: False for filter_name in self.FILTER_MAPPING.values()
            }
            
            for filter_name in selected_filters:
                if filter_name:
                    filter_params[filter_name] = True

            return {
                "command_type": "image_generation",
                "params": {
                    "prompt": prompt,
                    "userId": "247",
                    "aspectRatio": 0,
                    **filter_params
                }
            }
        return None

    def _check_nft_intent(self, lower_input: str, original_input: str) -> Optional[Dict[str, Any]]:
        """Check for NFT analysis intent"""
        nft_keywords = ['nft', 'collection', 'show my nft', 'get nft', 'view nft']
        
        if any(keyword in lower_input for keyword in nft_keywords):
            address = self._extract_eth_address(original_input)
            return {
                "command_type": "nft_analysis",
                "params": {
                    "address": address if address else None,
                    "network": "arbitrum"
                }
            }
        return None

    def _check_wallet_intent(self, lower_input: str, original_input: str) -> Optional[Dict[str, Any]]:
        """Check for wallet analysis intent"""
        address = self._extract_eth_address(original_input)
        
        if address:
            return {
                "command_type": "wallet_analysis",
                "params": {"address": address}
            }
        return None

    def _extract_character_name(self, text: str) -> str:
        """Extract character name from training request"""
        words = text.lower().split()
        try:
            char_index = -1
            for keyword in ['character', 'lora']:
                if keyword in words:
                    char_index = max(char_index, words.index(keyword) + 1)
            
            if char_index >= 0 and char_index < len(words):
                return words[char_index]
            return ""
        except ValueError:
            return ""

    def _extract_generation_prompt(self, text: str, keywords: List[str]) -> str:
        """Extract the actual prompt from image generation request"""
        prompt = text
        for keyword in keywords:
            prompt = prompt.replace(keyword, '').strip()
        return prompt

    def _extract_eth_address(self, text: str) -> Optional[str]:
        """Extract Ethereum address from text"""
        for word in text.split():
            if word.startswith('0x') and len(word) == 42:
                return word
        return None

    def _create_filter_prompt(self, prompt: str) -> str:
        """Create prompt for style filter selection"""
        return f"""Given this image generation request, which art style filter should be applied? 
Choose ONLY ONE filter from the following list that best matches the request's intent:
{', '.join(self.FILTER_MAPPING.keys())}

User request: "{prompt}"

Important rules:
1. If a specific character/style is mentioned, ONLY choose that one
2. If multiple styles are mentioned, prioritize the first one
3. Return ONLY ONE filter name, no commas, no explanations
4. If no specific style is mentioned, choose the most appropriate one
5. Be very careful not to mix up different characters/styles

Your response should be just ONE word from the available list, nothing else."""

    def _get_unknown_intent(self) -> Dict[str, Any]:
        """Return unknown intent structure"""
        return {
            "command_type": "unknown",
            "params": {}
        }