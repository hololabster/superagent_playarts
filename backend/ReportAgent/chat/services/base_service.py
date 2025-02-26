# base_service.py
import os
import json
import logging
from dotenv import load_dotenv
from web3 import Web3
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseService(ABC):
    def __init__(self):
        load_dotenv()
        self.rpc_url = os.getenv('RPC_URL')
        self.agent_url = os.getenv('AGENT_URL')
        self.bearer_token = os.getenv('BEARER_TOKEN')
        self.model = os.getenv('MODEL_NAME', 'phi4')
        
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers
        
    def generate_llm_response(self, prompt: str) -> Optional[str]:
            try:
                if not self.agent_url:
                    logger.error("LLM agent URL not configured")
                    return None

                logger.info(f"LLM request to: {self.agent_url}")
                logger.debug(f"Using model: {self.model}")
                logger.debug(f"Headers: {self._get_headers()}")
                # Don't log the full prompt but log its length
                logger.debug(f"Prompt length: {len(prompt)}")

                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
                logger.debug(f"Request payload (without prompt): {json.dumps({k:v for k,v in payload.items() if k != 'prompt'})}")

                response = requests.post(
                    self.agent_url,
                    json=payload,
                    headers=self._get_headers(),
                    verify=False,
                    timeout=60
                )

                logger.info(f"LLM response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"LLM API error status: {response.status_code}")
                    logger.error(f"LLM API error response: {response.text}")
                    return None

                try:
                    result = response.json()
                    logger.debug(f"Response keys: {list(result.keys())}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    logger.error(f"Raw response: {response.text[:500]}")
                    return None

                if "response" not in result:
                    logger.error(f"Unexpected response format. Available keys: {list(result.keys())}")
                    return None
                
                logger.info("Successfully received LLM response")
                return result.get("response")
                
            except requests.exceptions.Timeout:
                logger.error("LLM request timed out")
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM request failed: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in LLM request: {str(e)}")
                logger.exception("Full traceback:")
                return None
        
    def get_transfer_value(self, tx: Dict) -> float:
        """
        Extracts a 'direct' value (ETH or ERC-20) from a single transfer.
        """
        try:
            def hex_to_eth(hex_value: str) -> float:
                if not hex_value:
                    return 0.0
                try:
                    if hex_value.startswith('0x'):
                        wei = int(hex_value, 16)
                        return float(wei) / 1e18
                    return 0.0
                except ValueError:
                    return 0.0

            # 1. Direct value field
            if 'value' in tx:
                val = tx['value']
                if isinstance(val, str):
                    if val.startswith('0x'):
                        return hex_to_eth(val)
                    else:
                        try:
                            return float(val)
                        except:
                            pass
                elif isinstance(val, (int, float)):
                    return float(val)

            # 2. rawContract.value
            if 'rawContract' in tx and 'value' in tx['rawContract']:
                raw_val = tx['rawContract']['value']
                if isinstance(raw_val, str):
                    return hex_to_eth(raw_val)
                elif isinstance(raw_val, (int, float)):
                    return float(raw_val) / 1e18

            # 3. metadata.value
            metadata = tx.get('metadata', {})
            if 'value' in metadata:
                try:
                    return float(metadata['value'])
                except (ValueError, TypeError):
                    pass

            # 4. erc20 token transfer value (Alchemy response format)
            if 'erc20Metadata' in tx:
                erc20 = tx['erc20Metadata']
                if isinstance(erc20, dict):
                    raw_val = erc20.get('value')
                    decimals = erc20.get('decimals', 18)
                    if raw_val and raw_val.isdigit():
                        return float(raw_val) / (10 ** int(decimals))
            
            # 5. external transfer's ETH value
            if tx.get('category') == 'external' and tx.get('asset') == 'ETH':
                raw_val = tx.get('value')
                if isinstance(raw_val, str):
                    try:
                        return float(raw_val)
                    except ValueError:
                        pass
                elif isinstance(raw_val, (int, float)):
                    return float(raw_val)

            return 0.0

        except Exception as e:
            print(f"Error extracting value from tx: {str(e)}, tx data: {json.dumps(tx)[:200]}...")
            return 0.0

    def fetch_all_transfers(self, 
                          params: Dict[str, Any], 
                          endpoint: str, 
                          headers: Dict[str, str],
                          max_txs: int = 1000) -> List[Dict[str, Any]]:
        """
        Uses Alchemy's AssetTransfers API to fetch all transaction information via pagination.
        max_txs: 최대 몇 건까지 트랜잭션을 수집할 것인지 설정
        """
        transfers = []
        page_key = None

        try:
            while True:
                if page_key:
                    params["pageKey"] = page_key

                payload = {
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "alchemy_getAssetTransfers",
                    "params": [params]
                }

                response = requests.post(endpoint, json=payload, headers=headers)
                if response.status_code != 200:
                    print(f"API Error: Status code {response.status_code}")
                    print(f"Response text: {response.text}")
                    break

                data = response.json()
                if "error" in data:
                    print(f"API returned error: {data['error']}")
                    break

                new_transfers = data.get("result", {}).get("transfers", [])
                transfers.extend(new_transfers)

                # 만약 현재까지 누적된 트랜잭션이 max_txs보다 크면, 더 이상 가져오지 않고 중단
                if len(transfers) >= max_txs:
                    print(f"Reached the maximum limit of {max_txs} transactions. Stopping pagination.")
                    break

                page_key = data.get("result", {}).get("pageKey")
                if not page_key:
                    # 다음 페이지가 없으면 중단
                    break

            # 실제로는 max_txs를 초과해서 담겼을 수도 있으니 마지막에 슬라이싱
            return transfers[:max_txs]

        except Exception as e:
            print(f"Error in fetch_all_transfers: {str(e)}")
            return []