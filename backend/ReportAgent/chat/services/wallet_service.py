from .base_service import BaseService
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime
import json
import requests

class WalletService(BaseService):
    def analyze_wallet(self, address: str) -> str:
        """
        Takes a wallet address, creates a basic report and a deep analysis report (using the LLM),
        then combines them into a final report.
        """
        try:
            print("Starting wallet analysis...")
            wallet_data = self.get_wallet_analysis(address)
            if not wallet_data:
                return "Error occurred while fetching wallet data."
                
            print("1) Generating basic report...")
            basic_report = self.generate_basic_report(wallet_data, address)
            if not basic_report:
                return "Error occurred while generating the basic report."
                
            print("2) Generating LLM-based deep analysis report...")
            deep_analysis_report = self.analyze_transaction_data(wallet_data, address)
            if not deep_analysis_report:
                deep_analysis_report = "An error occurred during deep analysis."
                
            # Final output
            combined_report = f"{basic_report}\n\n---\n\n{deep_analysis_report}"
            return combined_report
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"An error occurred during wallet analysis. Details: {str(e)}"
        
    def get_wallet_analysis(self, address: str, max_txs: int = 10000) -> Dict[str, Any]:
        """
        (For wallet analysis) Retrieves basic info (balance, tx count) and recent transactions
        for the given wallet address.
        
        max_txs: 최대 몇 건의 트랜잭션만 가져올 것인지에 대한 파라미터 (기본값 1000)
        """
        try:
            print("Starting wallet analysis data fetching...")
            wallet_data = {
                'basic_info': {},
                'transactions': [],
                'tokens': []
            }
            
            checksum_address = self.web3.to_checksum_address(address)
            
            # Basic info
            balance_wei = self.web3.eth.get_balance(checksum_address)
            balance_eth = float(self.web3.from_wei(balance_wei, 'ether'))
            tx_count = self.web3.eth.get_transaction_count(checksum_address)
            
            wallet_data['basic_info'] = {
                'balance': balance_eth,
                'transaction_count': tx_count
            }

            # Alchemy Asset Transfers endpoint
            endpoint = self.rpc_url
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # (1) Check total number of transactions (이건 실제 on-chain 상 트랜잭션 추정치)
            #     단순히 최대 1000건만 가져와서 전체 tx 수 파악 가능 (API 제한).
            print("Checking total transaction count...")
            params_count = {
                "fromBlock": "0x0",
                "toBlock": "latest",
                "fromAddress": address,
                "category": ["external", "internal", "erc20", "erc721", "erc1155"],
                "withMetadata": True,
                "maxCount": "0x3e8"  # up to 1000
            }
            total_txs_data = self.fetch_all_transfers(params_count, endpoint, headers, max_txs=1000)
            # 실제 건수만 측정
            total_count = len(total_txs_data) if total_txs_data is not None else 0
            print(f"Found total {total_count} transactions (in first 1000 or fewer).")

            # (2) 실제로 가져올 fromBlock 범위 결정
            #     - total_count > max_txs 이면 "최근 7일" 혹은 "최근 N 블록"만 가져오도록 제한
            if total_count > max_txs:
                print(f"Transaction count exceeds {max_txs}, fetching last 7 days only...")
                current_block = self.web3.eth.block_number
                blocks_in_7_days = 7 * 24 * 60 * 60 // 12
                from_block = hex(current_block - blocks_in_7_days)
            else:
                print("Fetching all transactions from block 0...")
                from_block = "0x0"
            
            # (3) fromAddress, toAddress 각각 fetch
            print(f"Fetching transactions from block {from_block} to the latest, up to max {max_txs}...")
            
            params_from = {
                "fromBlock": from_block,
                "toBlock": "latest",
                "fromAddress": address,
                "category": ["external", "internal", "erc20", "erc721", "erc1155"],
                "withMetadata": True,
                "maxCount": "0x3e8",  # per page
                "excludeZeroValue": False
            }
            txs_from = self.fetch_all_transfers(params_from, endpoint, headers, max_txs=max_txs) or []
            print(f"Found {len(txs_from)} 'from' transactions (limited to {max_txs} max).")
            
            params_to = {
                "fromBlock": from_block,
                "toBlock": "latest",
                "toAddress": address,
                "category": ["external", "internal", "erc20", "erc721", "erc1155"],
                "withMetadata": True,
                "maxCount": "0x3e8",
                "excludeZeroValue": False
            }
            txs_to = self.fetch_all_transfers(params_to, endpoint, headers, max_txs=max_txs) or []
            print(f"Found {len(txs_to)} 'to' transactions (limited to {max_txs} max).")
            
            # (4) Merge & sort (timestamp desc), 그리고 최종 max_txs까지 잘라냄
            combined_txs = txs_from + txs_to
            combined_txs = sorted(
                combined_txs,
                key=lambda x: x.get('metadata', {}).get('blockTimestamp', ''),
                reverse=True
            )
            
            # 최종적으로 max_txs 개까지만 제한
            combined_txs = combined_txs[:max_txs]
            
            wallet_data['transactions'] = combined_txs
            return wallet_data
            
        except Exception as e:
            print(f"Error in wallet analysis: {str(e)}")
            return {}

        
    def process_transaction_details(self, tx: Dict[str, Any], address: str) -> Dict[str, Any]:
        """
        Processes the details of a single transaction and classifies it.
        """
        processed_tx = {
            'timestamp': tx.get('metadata', {}).get('blockTimestamp', 'N/A'),
            'block_number': tx.get('blockNum', 'N/A'),
            'category': tx.get('category', 'unknown'),
            'from': tx.get('from', 'N/A'),
            'to': tx.get('to', 'N/A'),
            'hash': tx.get('hash', 'N/A')
        }
        
        def safe_float_conversion(value) -> float:
            """Safely convert to float."""
            if value is None:
                return 0.0
            try:
                if isinstance(value, str):
                    value = ''.join(c for c in value if c.isdigit() or c == '.' or c == '-')
                return float(value)
            except (ValueError, TypeError):
                print(f"Warning: Could not convert value '{value}' to float")
                return 0.0
        
        # Simplify type identification based on category
        if tx.get('category') == 'erc20':
            processed_tx['type'] = 'ERC-20'
            processed_tx['token_symbol'] = tx.get('asset', 'Unknown')
            raw_value = tx.get('value')
            processed_tx['token_amount'] = safe_float_conversion(raw_value)
            processed_tx['token_decimals'] = tx.get('decimals', 18)
            processed_tx['direction'] = 'Outgoing' if tx['from'].lower() == address.lower() else 'Incoming'
            processed_tx['eth_value'] = 0.0
        else:
            processed_tx['type'] = 'ETH'
            raw_value = tx.get('value')
            processed_tx['eth_value'] = safe_float_conversion(raw_value)
            processed_tx['direction'] = 'Outgoing' if tx['from'].lower() == address.lower() else 'Incoming'
        
        return processed_tx
        
    def generate_basic_report(self, wallet_data: Dict[str, Any], address: str) -> str:
        """
        Generates a simple Markdown report summarizing the wallet data.
        """
        try:
            if not wallet_data:
                return "Error: No wallet data available."
                
            basic_info = wallet_data.get('basic_info', {})
            transactions = wallet_data.get('transactions', [])
            
            # Process transactions
            processed_txs = []
            for tx in transactions:
                try:
                    processed_tx = self.process_transaction_details(tx, address)
                    processed_txs.append(processed_tx)
                except Exception as e:
                    print(f"Error processing transaction: {e}")
                    continue
            
            # Separate ERC-20 and ETH transactions
            erc20_txs = [tx for tx in processed_txs if tx['type'] == 'ERC-20']
            eth_txs = [tx for tx in processed_txs if tx['type'] == 'ETH']
            
            report = [
                f"# Ethereum Wallet Analysis Report",
                f"**Target Address:** `{address}`\n",
                "## 1. Basic Information",
                f"- **ETH Balance**: {basic_info.get('balance', 0.0):.4f} ETH",
                f"- **Total Transactions**: {len(transactions)} (recent 7 days or overall)",
                f"  - ETH Transactions: {len(eth_txs)}",
                f"  - ERC-20 Token Transactions: {len(erc20_txs)}\n"
            ]
            
            # (2) ERC-20 token analysis
            if erc20_txs:
                report.append("## 2. ERC-20 Token Transactions Analysis")
                token_stats = defaultdict(lambda: {'Incoming': 0.0, 'Outgoing': 0.0, 'tx_count': 0})
                for tx in erc20_txs:
                    token = tx['token_symbol']
                    amount = tx['token_amount']
                    direction = tx['direction']
                    
                    token_stats[token][direction] += amount
                    token_stats[token]['tx_count'] += 1
                
                report.extend([
                    "### Statistics by Token",
                    "| Token | Transaction Count | Incoming | Outgoing | Net Change |",
                    "|-------|-------------------|----------|----------|-----------|"
                ])
                
                for token, stats in token_stats.items():
                    net_change = stats['Incoming'] - stats['Outgoing']
                    report.append(
                        f"| {token} | {stats['tx_count']} | "
                        f"{stats['Incoming']:.4f} | {stats['Outgoing']:.4f} | {net_change:+.4f} |"
                    )
                
                report.extend([
                    "\n### Recent ERC-20 Transactions (up to 10)",
                    "| Time | Token | Direction | Amount | Counterparty | Tx Hash |",
                    "|------|-------|----------|--------|-------------|---------|"
                ])
                
                for tx in sorted(erc20_txs, key=lambda x: x['timestamp'], reverse=True)[:10]:
                    report.append(
                        f"| {tx['timestamp']} | {tx['token_symbol']} | {tx['direction']} | "
                        f"{tx['token_amount']:.4f} | `{tx['to'] if tx['direction'] == 'Outgoing' else tx['from']}` | "
                        f"`{tx['hash']}` |"
                    )
            else:
                report.append("\n## 2. ERC-20 Token Transactions Analysis\nNo recent ERC-20 transactions.")
            
            # (3) ETH transaction analysis
            if eth_txs:
                report.append("\n## 3. ETH Transaction Analysis")
                eth_stats = {'Incoming': 0.0, 'Outgoing': 0.0, 'tx_count': len(eth_txs)}
                
                for tx in eth_txs:
                    eth_stats[tx['direction']] += tx['eth_value']
                
                net_change = eth_stats['Incoming'] - eth_stats['Outgoing']
                
                report.extend([
                    "### ETH Transaction Statistics",
                    f"- **Total Transaction Count**: {eth_stats['tx_count']}",
                    f"- **Total Incoming**: {eth_stats['Incoming']:.4f} ETH",
                    f"- **Total Outgoing**: {eth_stats['Outgoing']:.4f} ETH",
                    f"- **Net Change**: {net_change:+.4f} ETH\n",
                    "### Recent ETH Transactions (up to 10)",
                    "| Time | Direction | Amount (ETH) | Counterparty | Tx Hash |",
                    "|------|-----------|--------------|-------------|---------|"
                ])
                
                for tx in sorted(eth_txs, key=lambda x: x['timestamp'], reverse=True)[:10]:
                    report.append(
                        f"| {tx['timestamp']} | {tx['direction']} | {tx['eth_value']:.4f} | "
                        f"`{tx['to'] if tx['direction'] == 'Outgoing' else tx['from']}` | `{tx['hash']}` |"
                    )
            else:
                report.append("\n## 3. ETH Transaction Analysis\nNo recent ETH transactions.")
            
            return "\n".join(report)
            
        except Exception as e:
            print(f"Error generating basic report: {str(e)}")
            return "An error occurred while generating the report."
        
    def analyze_suspicious_activity(self, transactions: List[Dict[str, Any]], address: str) -> Dict[str, Any]:
        """
        Check transaction data for suspicious activity (phishing, blacklist associations, etc.).
        """
        blacklist_addresses = {
            "0xbaa44c7e27e125118d10c43ae6c9f0f5e094e144",
            "0x46705dfff24256421a05d056c29e81bdc09723b8",
        }

        if not transactions:
            return {
                "total_txs": 0,
                "blacklisted_count": 0,
                "suspicious_spam_count": 0,
                "suspicious": False,
                "details": "No transaction data available."
            }

        total_txs = len(transactions)
        
        blacklisted_txs = 0
        for tx in transactions:
            from_addr = tx.get('from', '').lower()
            to_addr = tx.get('to', '').lower()
            if from_addr in blacklist_addresses or to_addr in blacklist_addresses:
                blacklisted_txs += 1

        suspicious_spam_count = 0
        sorted_txs = sorted(
            transactions,
            key=lambda x: x.get('metadata', {}).get('blockTimestamp', ''),
            reverse=True
        )

        for i in range(len(sorted_txs) - 1):
            current_tx = sorted_txs[i]
            next_tx = sorted_txs[i + 1]
            
            current_time = current_tx.get('metadata', {}).get('blockTimestamp', '')
            next_time = next_tx.get('metadata', {}).get('blockTimestamp', '')
            
            if current_time and next_time:
                try:
                    current_dt = datetime.strptime(current_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                    next_dt = datetime.strptime(next_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                    time_diff = (current_dt - next_dt).total_seconds()
                    
                    if 0 <= time_diff <= 60:  # within 1 minute
                        suspicious_spam_count += 1
                except ValueError:
                    continue

        suspicious = (blacklisted_txs > 0) or (suspicious_spam_count >= 5)

        return {
            "total_txs": total_txs,
            "blacklisted_count": blacklisted_txs,
            "suspicious_spam_count": suspicious_spam_count,
            "suspicious": suspicious,
            "details": "Suspicious activity detected." if suspicious else "No special notes."
        }

    def analyze_transaction_data(self, wallet_data: Dict[str, Any], address: str) -> str:
        """
        Calculates statistics/metrics from transaction data and requests 'deep analysis' from the LLM.
        """
        if not wallet_data or "transactions" not in wallet_data:
            return "No transaction data to analyze."
            
        tx_list = wallet_data["transactions"]
        suspicious_info = self.analyze_suspicious_activity(tx_list, address)
        
        total_txs = suspicious_info["total_txs"]
        blacklisted_cnt = suspicious_info["blacklisted_count"]
        spam_cnt = suspicious_info["suspicious_spam_count"]
        suspicious_flag = suspicious_info["suspicious"]
        
        stats_summary = (
            f"Total Transactions: {total_txs}\n"
            f"Blacklisted Transactions: {blacklisted_cnt}\n"
            f"Number of consecutive transactions within 1 minute: {spam_cnt}\n"
            f"Suspicious Flag: {suspicious_flag}\n"
        )
        
        # Preview the latest 5 transactions
        tx_preview = json.dumps(tx_list[:5], indent=2)
        
        prompt = f"""
You are a professional blockchain analyst.
Please analyze the Ethereum wallet at address {address}.

Below is a summary of transaction statistics:
{stats_summary}

And here is a sample of the most recent 5 transactions:
{tx_preview}

Please examine the wallet's activity patterns, any suspicious transactions, security vulnerabilities (phishing, blacklist),
and any special observations. Provide warnings or cautions if necessary.

Notes:
1. Respond in English.
2. Try to explain specialized terminology simply.
3. The analysis should be objective and fact-based.
"""
        llm_analysis = self.generate_llm_response(prompt)  # generate_response를 generate_llm_response로 변경
        if not llm_analysis:
            llm_analysis = "(No LLM response received or an error occurred.)"
            
        final_report = (
            "## Deep Analysis Report\n\n"
            f"**Target Address**: `{address}`\n\n"
            "### Preliminary Statistics Summary\n"
            f"```\n{stats_summary}\n```\n\n"
            "### AI Analysis Result\n"
            f"{llm_analysis}\n"
        )
        
        return final_report
