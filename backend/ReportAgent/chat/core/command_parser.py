# command_parser.py
# No special changes for image training in this example; 
# It's handled in LLMService parse_intent.

from .command_types import Command, CommandType
from ..services.llm_service import LLMService

class CommandParser:
    def __init__(self):
        self.llm_service = LLMService()
    
    def parse(self, user_input: str) -> Command:
        # Simple rules-based parse (existing logic)
        lower_input = user_input.lower()
        
        if "nft" in lower_input:
            return Command(
                type=CommandType.NFT_ANALYSIS,
                params={},
                raw_input=user_input
            )
        if '0x' in user_input and len(user_input) >= 42:
            for word in user_input.split():
                if word.startswith('0x') and len(word) == 42:
                    return Command(
                        type=CommandType.WALLET_ANALYSIS,
                        params={"address": word},
                        raw_input=user_input
                    )
        
        return Command(
            type=CommandType.UNKNOWN,
            params={},
            raw_input=user_input
        )
