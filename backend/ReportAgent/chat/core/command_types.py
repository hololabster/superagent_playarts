# command_types.py
# English Comments. Korean Explanation in answer text only.

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any

class CommandType(Enum):
    WALLET_ANALYSIS = "wallet_analysis"
    NFT_ANALYSIS = "nft_analysis"
    IMAGE_GENERATION = "image_generation"
    IMAGE_TRAINING = "image_training"
    UNKNOWN = "unknown"

@dataclass
class Command:
    type: CommandType
    params: Dict[str, Any]
    raw_input: str
