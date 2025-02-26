from .base_service import BaseService
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict
from datetime import datetime
import json
import requests
import urllib3
from web3 import Web3
from web3.main import to_checksum_address
from web3.exceptions import ContractLogicError  # For handling contract call errors
import logging
import traceback  # 상단에 추가
logger = logging.getLogger(__name__)
# Disable HTTPS certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Minimal Standard ERC-721 ABI (focusing on tokenURI, ownerOf)
ERC721_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class NFTService(BaseService):
    def __init__(self):
        super().__init__()
        # Arbitrum 메인넷 RPC URL 사용
        self.network_rpcs = {
            'arbitrum': 'https://arb1.arbitrum.io/rpc',  # Arbitrum 공식 RPC
            'story': 'https://mainnet.storyrpc.io/'
        }

        # Arbitrum 네트워크로 Web3 초기화
        self.web3 = Web3(Web3.HTTPProvider(self.network_rpcs['arbitrum']))
        
        # 체인 ID 확인 (Arbitrum은 42161)
        try:
            chain_id = self.web3.eth.chain_id
            print(f"Connected to chain ID: {chain_id}")
            if chain_id != 42161:  # Arbitrum 체인 ID
                print("Warning: Not connected to Arbitrum network")
        except Exception as e:
            print(f"Error checking chain ID: {e}")

        self.ERC721_ABI = ERC721_ABI

    def get_token_metadata(self, contract_address: str, token_id: int) -> Dict[str, Any]:
        """
        Fetch token metadata from an ERC721 contract using standard tokenURI.
        """
        try:
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.ERC721_ABI
            )
            # Check if token exists by calling ownerOf
            try:
                owner = contract.functions.ownerOf(token_id).call()
                print(f"Token {token_id} owner: {owner}")
            except ContractLogicError:
                print(f"Token {token_id} does not exist or was burned.")
                return {}
            except Exception as e:
                print(f"Error calling ownerOf: {str(e)}")
                return {}
            # Retrieve tokenURI
            try:
                token_uri = contract.functions.tokenURI(token_id).call()
                print(f"Token URI: {token_uri}")
            except ContractLogicError:
                print(f"TokenURI call failed for token {token_id}. Possibly non-standard ERC721.")
                return {}
            except Exception as e:
                print(f"Unexpected error calling tokenURI: {str(e)}")
                return {}
            # Handle IPFS/arweave if needed
            if token_uri.startswith('ipfs://'):
                token_uri = token_uri.replace('ipfs://', 'https://ipfs.io/ipfs/')
            elif token_uri.startswith('ar://'):
                token_uri = f"https://arweave.net/{token_uri[5:]}"
            # Fetch metadata from tokenURI
            try:
                response = requests.get(token_uri, headers={'Accept': 'application/json'}, timeout=10)
                response.raise_for_status()
                metadata = response.json()
                # Process image field
                if 'image' in metadata:
                    image_url = metadata['image']
                    if image_url.startswith('ipfs://'):
                        metadata['image'] = image_url.replace('ipfs://', 'https://ipfs.io/ipfs/')
                    elif image_url.startswith('ar://'):
                        metadata['image'] = f"https://arweave.net/{image_url[5:]}"
                return metadata
            except requests.exceptions.RequestException as e:
                print(f"Error fetching metadata from {token_uri}: {str(e)}")
                return {}
        except Exception as e:
            print(f"Error in get_token_metadata: {str(e)}")
            return {}

    def get_collection_metadata(self, contract_address: str, token_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch metadata for multiple tokens from the same collection.
        """
        collection_metadata = []
        for token_id in token_ids:
            metadata = self.get_token_metadata(contract_address, token_id)
            if metadata:
                metadata['token_id'] = token_id
                collection_metadata.append(metadata)
        return collection_metadata

    def process_large_collection(self, contract_address: str, start_id: int, end_id: int) -> List[Dict[str, Any]]:
        """
        Process a large collection in batches with retries.
        """
        batch_size = 10
        max_retries = 3
        collection_data = []
        for batch_start in range(start_id, end_id + 1, batch_size):
            batch_end = min(batch_start + batch_size, end_id + 1)
            token_ids = list(range(batch_start, batch_end))
            retry_count = 0
            while retry_count < max_retries:
                try:
                    batch_metadata = self.get_collection_metadata(contract_address, token_ids)
                    collection_data.extend(batch_metadata)
                    break
                except Exception as e:
                    print(f"Error processing batch {batch_start}-{batch_end}: {str(e)}")
                    retry_count += 1
                    if retry_count == max_retries:
                        print(f"Failed to process batch after {max_retries} retries")
        return collection_data

    def get_nfts(self, address: str, network: str = 'arbitrum') -> Dict[str, Any]:
        """
        Retrieves NFTs owned by the given address.
        Uses optimized fetching with tokenURI calls for metadata.
        """
        try:
            if network not in self.network_rpcs:
                return {"status": "error", "message": f"Unsupported network: {network}"}
            # Convert to checksum address
            try:
                checksum_address = to_checksum_address(address)
            except Exception as e:
                return {"status": "error", "message": f"Invalid address format: {str(e)}"}
            # Fetch NFTs (optimized approach)
            nfts = self._fetch_nfts_optimized(checksum_address, network)
            if not nfts:
                return {"status": "success", "message": f"No NFTs found for address {address}", "data": {"nfts": []}}
            return {"status": "success", "message": f"Found {len(nfts)} NFTs", "data": {"nfts": nfts}}
        except Exception as e:
            print(f"Error in get_nfts: {str(e)}")
            return {"status": "error", "message": f"Error fetching NFTs: {str(e)}"}

    def _fetch_nfts_from_chain(self, address: str, rpc_url: str, network: str) -> List[Dict[str, Any]]:
        """
        Example method to manually iterate over token IDs (not recommended for large collections).
        """
        try:
            print(f"Starting NFT fetch for address {address}")
            contract_address = "0xcf3380edacfacc4503dae0906f5c021e39dbfe2d"
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.ERC721_ABI
            )
            all_nfts = []
            for token_id in range(1, 100):
                try:
                    owner = contract.functions.ownerOf(token_id).call()
                    if owner.lower() == address.lower():
                        token_uri = contract.functions.tokenURI(token_id).call()
                        print(f"Found NFT: Token ID {token_id}, URI={token_uri}")
                        nft_info = {
                            "network": network,
                            "walletAddress": contract_address,
                            "tokenId": hex(token_id),
                            "tokenUri": token_uri
                        }
                        all_nfts.append(nft_info)
                except ContractLogicError:
                    continue
                except Exception as e:
                    print(f"Error in ownerOf or tokenURI: {str(e)}")
                    continue
            return all_nfts
        except Exception as e:
            print(f"Error fetching NFTs: {str(e)}")
            return []

    def _fetch_token_metadata(self, contract_address: str, token_id: str) -> Dict[str, Any]:
        try:
            # Web3 연결 상태 확인
            if not self.web3.is_connected():
                print("Web3 is not connected")
                return {}

            # 체인 ID 확인 (반드시 Arbitrum이어야 함)
            chain_id = self.web3.eth.chain_id
            print(f"Connected to chain ID: {chain_id}")
            if chain_id != 42161:  # Arbitrum 체인 ID
                print("Error: Must be connected to Arbitrum network")
                return {}

            # 3. 컨트랙트 코드 존재 여부 확인
            code = self.web3.eth.get_code(Web3.to_checksum_address(contract_address))
            if len(code) == 0:
                print("No contract code found at the specified address")
                return {}

            # 4. 토큰 ID 변환
            decimal_token_id = int(token_id, 16) if isinstance(token_id, str) and token_id.startswith('0x') else int(token_id)

            # 5. 수정된 ERC721 ABI (최소한의 필수 항목만)
            minimal_abi = [
                {
                    "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
                    "name": "tokenURI",
                    "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]

            # 6. 컨트랙트 인스턴스 생성
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=minimal_abi
            )

            # 7. 낮은 수준의 호출 시도
            try:
                function_signature = "tokenURI(uint256)"
                function_selector = self.web3.keccak(text=function_signature)[:4]
                padded_token_id = decimal_token_id.to_bytes(32, 'big')
                
                result = self.web3.eth.call({
                    'to': Web3.to_checksum_address(contract_address),
                    'data': function_selector + padded_token_id,
                    'gas': 2000000  # 가스 리미트 증가
                })
                
                if len(result) > 0:
                    # 결과가 있으면 디코딩 시도
                    decoded = self.web3.codec.decode(['string'], result)
                    if decoded:
                        token_uri = decoded[0].strip('\x00')
                        print(f"Successfully retrieved token URI via low-level call: {token_uri}")
                        return {"token_uri": token_uri, "token_id": token_id}
                
            except Exception as e:
                print(f"Low-level call failed: {str(e)}")

            # 8. 기존 방식으로 시도
            try:
                token_uri = contract.functions.tokenURI(decimal_token_id).call({
                    'gas': 2000000  # 가스 리미트 증가
                })
                print(f"Successfully retrieved token URI via contract call: {token_uri}")
                return {"token_uri": token_uri, "token_id": token_id}
                
            except Exception as e:
                print(f"Contract call failed: {str(e)}")

            return {}

        except Exception as e:
            print(f"Error in _fetch_token_metadata: {str(e)}")
            traceback.print_exc()
            return {}        

    def _fetch_nfts_optimized(self, address: str, network: str) -> List[Dict[str, Any]]:
        """
        Optimized NFT fetching with improved error handling and metadata retrieval
        """
        try:
            alchemy_url = "https://arb-mainnet.g.alchemy.com/v2/6WEw2FPscS1i94eKq18ok9AE3hd-xA_5"
            url = f"{alchemy_url}/getNFTs/"
            params = {
                "owner": address,
                "withMetadata": True,
                "pageSize": 100,
                "contractAddresses[]": ["0xcf3380edacfacc4503dae0906f5c021e39dbfe2d"]
            }
            
            print(f"Fetching NFTs for address: {address}")
            response = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
            
            if response.status_code != 200:
                print(f"Alchemy API Error: {response.status_code}")
                print(response.text)
                return []

            result = response.json()
            owned_nfts = result.get("ownedNfts", [])
            print(f"Found {len(owned_nfts)} NFTs from Alchemy")
            
            nfts = []
            for nft in owned_nfts:
                try:
                    contract_addr = nft.get("contract", {}).get("address")
                    token_id = nft.get("id", {}).get("tokenId")
                    
                    if not (contract_addr and token_id):
                        continue
                    
                    print(f"\nProcessing NFT: Contract={contract_addr}, TokenID={token_id}")
                    
                    # Try to fetch on-chain metadata first
                    metadata = self._fetch_token_metadata(contract_addr, token_id)
                    
                    if not metadata:
                        print("Falling back to Alchemy metadata")
                        metadata = nft.get("metadata", {})
                        
                    if metadata:
                        nft_info = {
                            "contract_address": contract_addr,
                            "token_id": token_id,
                            "token_uri": metadata.get("token_uri", ""),
                            "name": metadata.get("name", f"NFT #{token_id}"),
                            "description": metadata.get("description", ""),
                            "image_url": metadata.get("image", ""),
                            "attributes": metadata.get("attributes", [])
                        }
                        nfts.append(nft_info)
                        print(f"Successfully processed NFT {token_id}")
                    else:
                        print(f"No metadata available for token {token_id}")
                        
                except Exception as e:
                    print(f"Error processing NFT {token_id}: {str(e)}")
                    continue
                    
            return nfts
            
        except Exception as e:
            print(f"Error in _fetch_nfts_optimized: {str(e)}")
            return []

    def _get_cached_token_uri(self, contract_address: str, token_id: int) -> Optional[str]:
        """
        (Optional) If you have caching logic, implement it here.
        """
        return None

    def _process_nft_metadata(self, nfts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes NFT metadata (e.g. adjusting IPFS URL or adding collection info).
        """
        processed_nfts = []
        for nft in nfts:
            try:
                contract_address = nft.get("contract_address")
                token_id = nft.get("token_id")
                processed_nft = {
                    "contract_address": contract_address,
                    "token_id": token_id,
                    "name": nft.get("name", ""),
                    "description": nft.get("description", ""),
                    "image_url": nft.get("image_url", ""),
                    "attributes": nft.get("attributes", []),
                    "collection": {
                        "name": "PlayartsGotchaWhale"
                    }
                }
                processed_nfts.append(processed_nft)
            except Exception as e:
                print(f"Error processing NFT metadata: {str(e)}")
                continue
        return processed_nfts

    def _process_story_response(self, response_data: Dict[str, Any], address: str) -> List[Dict[str, Any]]:
        """
        Example placeholder for Story Network responses.
        """
        try:
            result = response_data.get("result")
            if not result:
                return []
            balance = int(result, 16)
            if balance == 0:
                return []
            nfts = []
            for token_id in range(balance):
                nft_info = {
                    "contract": {"address": address},
                    "id": {"tokenId": str(token_id)},
                    "metadata": {
                        "name": f"Story NFT #{token_id}",
                        "description": "Story Network NFT"
                    }
                }
                nfts.append(nft_info)
            return nfts
        except Exception as e:
            print(f"Error processing Story response: {str(e)}")
            return []

    def analyze_nft_market(self, days: int = 7, max_transactions: int = 50000) -> Dict[str, Any]:
        """
        NFT market analysis: fetch transactions, group by tx hash, identify actual sales/transfers,
        and collect collection-wise statistics.
        """
        try:
            print("Starting NFT market analysis...")
            # 하드코딩된 Alchemy URL 사용 (fetch_nfts_optimized와 일치시킴)
            alchemy_url = "https://eth-mainnet.g.alchemy.com/v2/6WEw2FPscS1i94eKq18ok9AE3hd-xA_5"
            
            current_block = self.web3.eth.block_number
            blocks_in_period = days * 24 * 60 * 60 // 12
            from_block = hex(current_block - blocks_in_period)
        
            # Major marketplace addresses
            MARKETPLACES = {
                "0x00000000006c3852cbef3e08e8df289169ede581": "OpenSea (Seaport 1.1)",
                "0x00000000000001ad428e4906ae43d8f9852d0dd6": "OpenSea (Seaport 1.5)",
                "0x00000000000000adc04c56bf30ac9d3c0aaf14dc": "OpenSea (Seaport 1.4)",
                "0x7be8076f4ea4a4ad08075c2508e481d6c946d12b": "OpenSea (Wyvern)",
                "0x000000000000ad05ccc4f10045630fb830b95127": "Blur",
                "0x39da41747a83aee658334415666f3ef92dd0d541": "Blur",
                "0x74312363e45dcaba76c59ec49a7aa8a65a67eed3": "X2Y2",
                "0x59728544b08ab483533076417fbbb2fd0b17ce3a": "LooksRare",
                "0x41a322b28d0ff354040e2cbc676f0320d8c8850d": "LooksRare v1",
                "0x7f268357a8c2552623316e2562d90e642bb538e5": "Rarible",
                "0x4fee7b061c97c9c496b01dbce9cdb10c02f0a0be": "Rarible v2",
                "0x2b2e8cda09bba9660dca5cb6233787738ad68329": "SudoSwap",
                "0x0fc584529a2aefa997697fafacba5831fac0c22d": "NFTX"
            }
            params = {
                "fromBlock": from_block,
                "toBlock": "latest",
                "category": ["erc721", "erc1155", "external", "erc20", "internal"],
                "withMetadata": True,
                "maxCount": "0x3e8"
            }
            all_transfers = []
            page_key = None
            first_batch = True
            while len(all_transfers) < max_transactions:
                try:
                    if page_key:
                        params["pageKey"] = page_key
                    payload = {
                        "id": 1,
                        "jsonrpc": "2.0",
                        "method": "alchemy_getAssetTransfers",
                        "params": [params]
                    }
                    response = requests.post(
                        alchemy_url,  # self.rpc_url 대신 alchemy_url 사용
                        json=payload,
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                        timeout=120
                    )
                    if response.status_code != 200:
                        print(f"API Error: {response.status_code}")
                        break
                    data = response.json()
                    if "error" in data:
                        print(f"API Error: {data['error']}")
                        break
                    transfers = data.get("result", {}).get("transfers", [])
                    if first_batch and transfers:
                        sample_tx = transfers[0]
                        print("First batch sample transfer:")
                        print(json.dumps(sample_tx, indent=2))
                        val = self.get_transfer_value(sample_tx)
                        print(f"Extracted value: {val} ETH")
                        first_batch = False
                    all_transfers.extend(transfers)
                    print(f"Collected {len(all_transfers)} transfers so far...")
                    page_key = data.get("result", {}).get("pageKey")
                    if not page_key:
                        break
                except Exception as e:
                    print(f"Error fetching transfers: {e}")
                    break
            print(f"\nTotal transfers collected: {len(all_transfers)}")
            grouped_transfers = defaultdict(list)
            for tx in all_transfers:
                tx_hash = tx.get('hash')
                if tx_hash:
                    grouped_transfers[tx_hash].append(tx)
            collection_stats = defaultdict(lambda: {
                'volume_eth': 0.0,
                'transactions': 0,
                'sales': 0,
                'transfers': 0,
                'unique_buyers': set(),
                'unique_sellers': set(),
                'price_history': [],
                'floor_price': float('inf'),
                'highest_price': 0.0,
                'marketplace_stats': defaultdict(int),
                'daily_volume_eth': 0.0,
                'daily_sales': 0,
                'price_trend': 0.0,
                'liquidity_score': 0.0,
                'token_ids': set()
            })
            for tx_hash, transfers_in_one_tx in grouped_transfers.items():
                nft_transfers = []
                for t in transfers_in_one_tx:
                    cat = t.get('category', '')
                    if cat in ('erc721', 'erc1155'):
                        nft_transfers.append(t)
                if not nft_transfers:
                    continue
                payment_transfers = []
                for t in transfers_in_one_tx:
                    cat = t.get('category', '')
                    if cat in ('external', 'internal', 'erc20'):
                        val = self.get_transfer_value(t)
                        if val > 0:
                            payment_transfers.append(t)
                used_marketplace = None
                for t in transfers_in_one_tx:
                    from_addr = t.get('from', '').lower()
                    to_addr = t.get('to', '').lower()
                    for mp_addr, mp_name in MARKETPLACES.items():
                        if mp_addr.lower() in [from_addr, to_addr]:
                            used_marketplace = mp_name
                            break
                    if used_marketplace:
                        break
                for nft_tx in nft_transfers:
                    contract_address = nft_tx.get('rawContract', {}).get('address', '').lower()
                    token_id = nft_tx.get('tokenId')
                    from_addr = nft_tx.get('from', '').lower()
                    to_addr = nft_tx.get('to', '').lower()
                    stats = collection_stats[contract_address]
                    stats['transactions'] += 1
                    if token_id:
                        stats['token_ids'].add(token_id)
                    sale_price = 0.0
                    is_sale = False
                    max_payment = 0.0
                    for pay_tx in payment_transfers:
                        pay_from = pay_tx.get('from', '').lower()
                        pay_to = pay_tx.get('to', '').lower()
                        val = self.get_transfer_value(pay_tx)
                        if val > 0 and pay_from == to_addr and pay_to == from_addr:
                            if val > max_payment:
                                max_payment = val
                    if max_payment > 0:
                        is_sale = True
                        sale_price = max_payment
                    if is_sale:
                        stats['sales'] += 1
                        stats['volume_eth'] += sale_price
                        stats['unique_buyers'].add(to_addr)
                        stats['unique_sellers'].add(from_addr)
                        if sale_price < stats['floor_price']:
                            stats['floor_price'] = sale_price
                        if sale_price > stats['highest_price']:
                            stats['highest_price'] = sale_price
                        price_record = {
                            'price': sale_price,
                            'timestamp': nft_tx.get('metadata', {}).get('blockTimestamp'),
                            'marketplace': used_marketplace if used_marketplace else "Unknown",
                            'token_id': token_id
                        }
                        stats['price_history'].append(price_record)
                        if used_marketplace:
                            stats['marketplace_stats'][used_marketplace] += 1
                    else:
                        stats['transfers'] += 1
            for contract, stats in collection_stats.items():
                if stats['floor_price'] == float('inf'):
                    stats['floor_price'] = 0.0
                stats['daily_volume_eth'] = stats['volume_eth'] / days if days else stats['volume_eth']
                stats['daily_sales'] = stats['sales'] / days if days else stats['sales']
                if len(stats['price_history']) >= 2:
                    sorted_history = sorted(stats['price_history'], key=lambda x: x['timestamp'])
                    first_price = sorted_history[0]['price']
                    last_price = sorted_history[-1]['price']
                    if first_price > 0:
                        stats['price_trend'] = ((last_price - first_price) / first_price) * 100
                    else:
                        stats['price_trend'] = 0.0
                else:
                    stats['price_trend'] = 0.0
                unique_traders = len(stats['unique_buyers'] | stats['unique_sellers'])
                if stats['sales'] > 0:
                    stats['liquidity_score'] = (unique_traders / stats['sales']) * (stats['daily_sales'] / 10)
                else:
                    stats['liquidity_score'] = 0.0
                if stats['sales'] > 0:
                    total_sales_in_col = stats['sales']
                    stats['marketplace_distribution'] = {
                        mp: (cnt / total_sales_in_col * 100)
                        for mp, cnt in stats['marketplace_stats'].items()
                    }
                else:
                    stats['marketplace_distribution'] = {}
                stats['unique_buyers'] = list(stats['unique_buyers'])
                stats['unique_sellers'] = list(stats['unique_sellers'])
                stats['token_ids'] = list(stats['token_ids'])
            print(f"\nProcessed {len(collection_stats)} unique NFT collections")
            return collection_stats
        except Exception as e:
            print(f"Error in NFT market analysis: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def collect_advanced_nft_data(self, collection_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect extended data for each collection (rarity, whale ratio, security score, etc.).
        """
        advanced_data = {}
        for contract, stats in collection_stats.items():
            if stats['sales'] > 0:
                if stats['floor_price'] >= 3.0:
                    rarity_score = 8.5
                else:
                    rarity_score = 5.0
            else:
                rarity_score = 2.0
            holders = set(stats['unique_buyers']) | set(stats['unique_sellers'])
            unique_holders = len(holders)
            if unique_holders > 0 and stats['sales'] > 10:
                whale_ratio = 10 / unique_holders * 100
            else:
                whale_ratio = 3.0
            security_score = 7.0
            advanced_data[contract] = {
                "rarity_score": rarity_score,
                "whale_ratio": whale_ratio,
                "security_score": security_score
            }
        return advanced_data

    def generate_nft_report(self, collection_stats: Dict[str, Any]) -> str:
        """
        Basic NFT market summary report:
          - Top 10 popular collections
          - Overall market stats
          - Marketplace share, etc.
        """
        if not collection_stats:
            return "No NFT data to analyze."
        print("\nDebug Info: Generating basic NFT report...")
        total_volume_eth = sum(s['volume_eth'] for s in collection_stats.values())
        total_txs = sum(s['transactions'] for s in collection_stats.values())
        total_sales = sum(s['sales'] for s in collection_stats.values())
        sorted_collections = sorted(
            [(addr, s) for addr, s in collection_stats.items() if s['volume_eth'] > 0],
            key=lambda x: x[1]['volume_eth'],
            reverse=True
        )
        report = [
            "# NFT Market Analysis Report (Last 7 Days)\n",
            "## Popular NFT Collections (Top 10 by volume)\n"
        ]
        if sorted_collections:
            for addr, stats in sorted_collections[:10]:
                report.extend([
                    f"### NFT Collection: {addr}",
                    f"- **Volume (ETH)**: {stats['volume_eth']:.2f} ETH",
                    f"- **Total Transactions**: {stats['transactions']}",
                    f"  - Actual Sales: {stats['sales']}",
                    f"  - Simple Transfers: {stats['transfers']}",
                    f"- **Daily Average Volume**: {stats['daily_volume_eth']:.2f} ETH",
                    f"- **Floor Price**: {stats['floor_price']:.3f} ETH",
                    f"- **Highest Price**: {stats['highest_price']:.3f} ETH",
                    f"- **Unique Buyers**: {len(stats['unique_buyers'])}",
                    f"- **Unique Sellers**: {len(stats['unique_sellers'])}",
                    ""
                ])
                if stats.get('marketplace_distribution'):
                    report.append("**Marketplace Distribution:**")
                    for mp, percentage in stats['marketplace_distribution'].items():
                        report.append(f"- {mp}: {percentage:.1f}%")
                    report.append("")
                report.append(f"**Price Trend (comparing start to end)**: {stats.get('price_trend', 0):+.1f}%\n")
        else:
            report.append("No collections with actual sales volume found.\n")
        active_collections = len([s for s in collection_stats.values() if s['volume_eth'] > 0])
        report.extend([
            "\n## Market Summary",
            f"- **Total Collections Analyzed**: {len(collection_stats)}",
            f"- **Collections with Actual Sales**: {active_collections}",
            f"- **Total ETH Volume**: {total_volume_eth:.1f} ETH",
            f"- **Total Transactions**: {total_txs}",
            f"  - Actual Sales: {total_sales}",
            f"  - Simple Transfers: {total_txs - total_sales}",
            f"- **Average Sale Price**: {(total_volume_eth/total_sales if total_sales > 0 else 0):.3f} ETH"
        ])
        all_marketplace_stats = defaultdict(int)
        for s in collection_stats.values():
            for mp, cnt in s['marketplace_stats'].items():
                all_marketplace_stats[mp] += cnt
        if all_marketplace_stats:
            total_mp_sales = sum(all_marketplace_stats.values())
            report.extend([
                "\n### Marketplace Share",
                "| Marketplace | Sales Count | Share |",
                "|-------------|------------:|------:|"
            ])
            sorted_mp = sorted(all_marketplace_stats.items(), key=lambda x: x[1], reverse=True)
            for mp, cnt in sorted_mp:
                share = (cnt / total_mp_sales * 100) if total_mp_sales else 0
                report.append(f"| {mp} | {cnt} | {share:.1f}% |")
        return "\n".join(report)

    def process_nft_analysis(self) -> str:
        """
        Perform general NFT market analysis without requiring a specific wallet address.
        Analyzes recent transactions, market trends, and generates comprehensive report.
        """
        try:
            logger.info("Starting general NFT market analysis...")
            blocks_to_analyze = 10000
            days = blocks_to_analyze * 12 // (24 * 60 * 60)  # ~12 sec per block
            collection_stats = self.analyze_nft_market(days=days, max_transactions=10000)
            if not collection_stats:
                return "No NFT market data available for analysis."
            advanced_data = self.collect_advanced_nft_data(collection_stats)
            base_report = self.generate_nft_report(collection_stats)
            deep_report = self.generate_nft_deep_analysis(collection_stats, advanced_data)
            final_report = (
                f"# NFT Market Analysis Report\n"
                f"Analyzing approximately last {blocks_to_analyze} blocks (~{days} days)\n\n"
                f"{base_report}\n\n"
                f"---\n\n"
                f"{deep_report}"
            )
            return final_report
        except Exception as e:
            logger.error(f"Error during NFT analysis: {str(e)}", exc_info=True)
            return "An error occurred during NFT market analysis."

    def generate_nft_deep_analysis(self, collection_stats: Dict[str, Any], advanced_data: Dict[str, Any]) -> str:
        """
        Uses extended data (rarity, whale ratio, security score) plus basic stats for an LLM-based deep analysis.
        """
        try:
            sorted_collections = sorted(
                collection_stats.items(),
                key=lambda x: x[1].get('volume_eth', 0),
                reverse=True
            )[:10]
            combined_summary = []
            for contract, stats in sorted_collections:
                adv = advanced_data.get(contract, {})
                volume_7d = stats.get('volume_eth', 0)
                avg_price = volume_7d / stats.get('sales', 1) if stats.get('sales', 0) > 0 else 0
                summary_item = {
                    "contract_address": contract,
                    "collection_name": stats.get('collection', {}).get('name', 'Unknown Collection'),
                    "volume_7d_eth": round(volume_7d, 2),
                    "sales_count": stats.get('sales', 0),
                    "floor_price_eth": round(stats.get('floor_price', 0), 3),
                    "avg_price_eth": round(avg_price, 3),
                    "unique_holders": len(set(stats.get('unique_buyers', []) + stats.get('unique_sellers', []))),
                    "rarity_score": round(adv.get('rarity_score', 0), 1),
                    "whale_ratio": round(adv.get('whale_ratio', 0), 1),
                    "security_score": round(adv.get('security_score', 0), 1),
                    "price_trend_7d": round(stats.get('price_trend', 0), 1)
                }
                combined_summary.append(summary_item)
            prompt = f"""As an NFT market expert, analyze the following NFT collection data from the past 7 days.

Collection Data (Top {len(combined_summary)} by volume):
{json.dumps(combined_summary, indent=2)}

Please provide a comprehensive market analysis covering:

1. Market Overview:
- Overall market trends
- Notable price movements
- Trading volume analysis

2. Collection-Specific Analysis:
- Standout collections and their performance
- Collections with high rarity scores and their characteristics
- Impact of whale activity on prices

3. Risk Assessment:
- Security considerations for featured collections
- Market manipulation risks
- Liquidity concerns

4. Future Outlook:
- Potential growth opportunities
- Risk factors to watch
- Market sentiment indicators

Format your response in clear sections with specific examples and data points to support your analysis.
Keep the analysis fact-based and avoid speculation."""
            logger.info("Requesting LLM analysis...")
            # Simulated LLM response for demonstration purposes
            llm_response = "Simulated LLM analysis based on provided NFT collection data."
            if not llm_response:
                logger.error("Failed to get LLM response")
                return "Unable to generate market analysis at this time. Please check the statistical data above for market insights."
            return f"## NFT Deep Analysis\n\n{llm_response}"
        except Exception as e:
            logger.error(f"Error generating deep analysis: {str(e)}", exc_info=True)
            return "Error generating market analysis. Please refer to the statistical data above."

    def get_image_url_from_token_uri(self, token_uri):
        """주어진 tokenURI에서 NFT 메타데이터를 가져와서 image_url을 반환함.
        IPFS 변환은 하지 않고, URL 그대로 사용.
        (내부 테스트를 위해 'https://api-ai-alpha.playarts.ai'를 'http://localhost:5001'로 변환)
        """
        # 내부 테스트용 URI 변환 (필요 시 활성화)
        internal_uri = token_uri
        if 'https://api-ai-alpha.playarts.ai' in internal_uri:
            internal_uri = internal_uri.replace('https://api-ai-alpha.playarts.ai', 'http://localhost:5001')
        elif 'https://api-ai-staging.playarts.ai' in internal_uri:
            internal_uri = internal_uri.replace('https://api-ai-staging.playarts.ai', 'http://localhost:5001')
        try:
            logger.info(f"Fetching NFT metadata from {internal_uri}")
            response = requests.get(internal_uri, timeout=10)
            response.raise_for_status()
            metadata = response.json()
            logger.info(f"Metadata response: {json.dumps(metadata, indent=2)}")
            
            # JSON에서 이미지 URL 가져오기
            image_url = metadata.get("image")
            if not image_url:
                image_url = metadata.get("image_url")
            if not image_url:
                image_url = metadata.get("animation_url")
            
            logger.info(f"Final image URL: {image_url}")
            return image_url
        except requests.RequestException as e:
            logger.error(f"Error fetching NFT metadata from {internal_uri}: {e}")
            return None