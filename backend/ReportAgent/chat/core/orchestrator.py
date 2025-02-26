# command_orchestrator.py
from typing import Dict, Any, Optional
import logging
from .command_types import CommandType 
from ..services.wallet_service import WalletService
from ..services.nft_service import NFTService
from ..services.llm_service import LLMService
from ..services.image_service import ImageService
import requests
import json
logger = logging.getLogger(__name__)

class CommandOrchestrator:
    """
    Orchestrates command processing and service interactions
    """
    
    def __init__(self):
        self.wallet_service = WalletService()
        self.nft_service = NFTService()
        self.llm_service = LLMService()
        self.image_service = ImageService()

    def process_input(self, user_input: str) -> str:
        try:
            logger.info(f"Processing input: {user_input}")
            intent = self.llm_service.parse_intent(user_input)
            command_type = intent["command_type"]
            params = intent["params"]
            logger.info(f"Detected command type: {command_type}")
            logger.debug(f"Parameters: {params}")
            
            # If command type is "unknown", send directly to LLM
            if command_type == "unknown":
                logger.info("Command type is unknown, forwarding directly to LLM")
                return self._handle_direct_llm_query(user_input)
                
            return self._route_command(command_type, params)
        except Exception as e:
            logger.error(f"Error in process_input: {str(e)}", exc_info=True)
            return f"An error occurred while processing your request: {str(e)}"

    def _handle_direct_llm_query(self, user_input: str) -> str:
        """
        Forward unknown queries directly to the LLM service
        """
        try:
            logger.info(f"Sending direct query to LLM: {user_input[:50]}...")
            
            # Generate a response through the LLM service
            response = self.llm_service.generate_llm_response(user_input)
            
            if not response:
                return "I'm sorry, I couldn't generate a response to your question. Please try again."
                
            return response
            
        except Exception as e:
            logger.error(f"Error in direct LLM query: {str(e)}", exc_info=True)
            return f"An error occurred while generating a response: {str(e)}"

    def _handle_image_training_upload(self, params: Dict[str, Any]) -> str:
        """
        Return an HTML form & JS for uploading local images only
        """
        forms_html = (
            "**Local Image Training**\n\n"
            "```html\n"
            "<form id='uploadTrainingForm' class='training-form'>\n"
            "  <div>\n"
            "    <label>Character Name:</label>\n"
            "    <input type='text' id='characterName' required>\n"
            "  </div>\n"
            "  <div>\n"
            "    <label>Upload Image:</label>\n"
            "    <input type='file' id='characterImage' accept='image/*' required>\n"
            "  </div>\n"
            "  <button type='submit'>Start Training (Upload)</button>\n"
            "</form>\n"
            "```\n\n"
            "```javascript\n"
            "document.getElementById('uploadTrainingForm').onsubmit = function(e) {\n"
            "  e.preventDefault();\n"
            "  // client-side JS logic to POST /api/upload_training_image/\n"
            "  // with FormData { character_name, character_image }\n"
            "};\n"
            "```"
        )
        return forms_html

    def _handle_image_training_nft(self, params: Dict[str, Any]) -> str:
        """
        Returns a single form that asks for:
        - Character Name (once)
        - Wallet Address
        Then a 'Search NFTs' button, 
        Once NFTs are fetched, show a <select> to pick one,
        and a 'Start Training' button to submit.
        """
        forms_html = (
            "<div class='training-section'>"
            "  <form id='nftTrainingForm' class='training-form mb-4'>"
            "    <div class='form-group'>"
            "      <label for='characterName'>Character Name:</label>"
            "      <input type='text' id='characterName' name='character_name' "
            "             class='form-control' required>"
            "    </div>"
            "    <div class='form-group'>"
            "      <label for='walletAddress'>NFT Wallet Address:</label>"
            "      <input type='text' id='walletAddress' name='wallet_address' "
            "             class='form-control' placeholder='Enter your wallet address (0x...)' "
            "             required>"
            "    </div>"
            "    <button type='button' id='nftSearchButton' class='btn btn-secondary'>"
            "      Search NFTs"
            "    </button>"

            "    <!-- NFT selection area: Initially hidden, shown on successful search -->"
            "    <div class='form-group mt-3' style='display:none;' id='nftSelectGroup'>"
            "      <label for='nftImageSelect'>Select NFT Image:</label>"
            "      <select id='nftImageSelect' name='nft_image_url' class='form-control'>"
            "        <option value=''>Choose an NFT image...</option>"
            "      </select>"
            "    </div>"

            "    <!-- Training start button: Initially hidden, shown when NFTs are loaded -->"
            "    <button type='submit' class='btn btn-primary mt-3' "
            "            style='display:none;' id='startNftTrainingBtn'>"
            "      Start Training with NFT"
            "    </button>"
            "  </form>"
            "</div>"
        )
        return forms_html


    def _route_command(self, command_type: str, params: Dict[str, Any]) -> str:
        try:
            if command_type == "wallet_analysis":
                return self._handle_wallet_analysis(params)
            elif command_type == "nft_analysis":
                return self._handle_nft_analysis(params)
            elif command_type == "image_generation":
                return self._handle_image_generation(params)
            elif command_type == "image_training_upload":
                return self._handle_image_training_upload(params)
            elif command_type == "image_training_nft":
                return self._handle_image_training_nft(params)
            else:
                return "No valid command found. Please try a different request."
        except Exception as e:
            logger.error(f"Error routing command {command_type}: {str(e)}", exc_info=True)
            return f"Error processing command: {str(e)}"

    def _handle_wallet_analysis(self, params: Dict[str, Any]) -> str:
        """Handle wallet analysis command"""
        address = params.get("address")
        if not address:
            return "Please provide a wallet address for analysis"
        return self.wallet_service.analyze_wallet(address)

    def _handle_image_generation(self, params: Dict[str, Any]) -> str:
        """Handle image generation command"""
        result = self.image_service.generate_image(params)
        if result["status"] == "success":
            return f"Generated image:\n\n![Generated Image]({result['data'].get('mediaUrl', '')})"
        return f"Error generating image: {result.get('message', 'Unknown error')}"

    def _handle_image_training(self, params: Dict[str, Any]) -> str:
        """Handle image training command"""
        # Show the form even if character_name is missing
        return self._handle_image_training_request()

    def _fetch_nft_metadata_from_uri(self, uri: str) -> Dict[str, Any]:
        try:
            # Replace api-ai-alpha.playarts.ai with localhost:5001
            internal_uri = uri.replace('https://api-ai-alpha.playarts.ai', 'http://localhost:5001')
            
            response = requests.get(internal_uri, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching metadata from {uri}: {str(e)}")
            return {}

    def _format_nft_response(self, nfts: list) -> str:
        """
        Format NFT analysis response with fetched metadata
        """
        if not nfts:
            return "No NFT metadata available"
            
        response_parts = ["### NFT Analysis Results\n"]
        
        for nft in nfts:
            # Fetch metadata from tokenURI
            metadata = {}
            if token_uri := nft.get('token_uri'):
                metadata = self._fetch_nft_metadata_from_uri(token_uri)
            
            # Combine fetched metadata with existing NFT data
            nft_data = {
                'name': metadata.get('name', 'Unnamed NFT'),
                'contract_address': nft.get('contract_address', 'N/A'),
                'token_id': nft.get('token_id', 'N/A'),
                'collection': {'name': metadata.get('collection_name', 'PlayartsGotchaWhale')},
                'description': metadata.get('description', 'N/A'),
                'attributes': metadata.get('attributes', []),
                'image_url': metadata.get('image', 'N/A')
            }
            
            response_parts.extend([
                f"#### {nft_data['name']}",
                f"- Contract: {nft_data['contract_address']}",
                f"- Token ID: {nft_data['token_id']}",
                f"- Collection: {nft_data['collection']['name']}",
                f"- Description: {nft_data['description']}",
                f"- Image URL: {nft_data['image_url']}",
                "",
                "**Attributes:**"
            ])
            
            for attr in nft_data['attributes']:
                response_parts.append(f"- {attr.get('trait_type', 'N/A')}: {attr.get('value', 'N/A')}")
            
            response_parts.append("\n---\n")
            
        return "\n".join(response_parts)


    def _handle_image_training_request(self) -> str:
        """
        Return HTML+JS form for both image upload and NFT search

        - 'Local Image Training' section: character name + file upload
        - 'NFT Training' section: (A) wallet address -> NFT search -> select, (B) character name input then train
        """
        forms_html = (
            # Markdown format assumed for chat display
            "### Character Training Setup\n\n"
            "```html\n"
            "<div class='training-section'>\n"

            "  <!-- 1) Local image upload section -->\n"
            "  <h5>Local Image Training</h5>\n"
            "  <form id='localTrainingForm' class='training-form mb-4'>\n"
            "    <div class='form-group'>\n"
            "      <label>Character Name (Local):</label><br>\n"
            "      <input type='text' id='localCharName' name='character_name' required\n"
            "             placeholder='Enter character name' class='form-control'>\n"
            "    </div>\n"
            "    <div class='form-group'>\n"
            "      <label>Upload Image:</label><br>\n"
            "      <input type='file' id='localImageFile' name='character_image' accept='image/*' required\n"
            "             class='form-control'>\n"
            "    </div>\n"
            "    <button type='submit' class='btn btn-primary'>Start Training (Upload)</button>\n"
            "  </form>\n\n"

            "  <!-- 2) NFT training section -->\n"
            "  <h5>Train via NFT</h5>\n"
            "  <form id='nftSearchForm' class='training-form mb-2'>\n"
            "    <div class='form-group'>\n"
            "      <label>Wallet Address:</label><br>\n"
            "      <input type='text' id='nftWalletAddress' placeholder='0x1234...' required\n"
            "             class='form-control'>\n"
            "    </div>\n"
            "    <button type='button' id='nftSearchButton' class='btn btn-secondary'>Search NFTs</button>\n"
            "  </form>\n\n"
            "  <!-- NFT list display + character name + Start Training -->\n"
            "  <form id='nftTrainingForm' class='training-form mt-3' style='display:none;'>\n"
            "    <div class='form-group'>\n"
            "      <label>Select NFT:</label><br>\n"
            "      <select id='nftSelect' class='form-control'>\n"
            "        <option value=''>Choose an NFT image...</option>\n"
            "      </select>\n"
            "    </div>\n"
            "    <!-- Separate character name input for NFT training -->\n"
            "    <div class='form-group mt-2'>\n"
            "      <label>Character Name (NFT):</label><br>\n"
            "      <input type='text' id='nftCharName' required\n"
            "             placeholder='Enter character name for NFT' class='form-control'>\n"
            "    </div>\n"
            "    <button type='submit' id='nftTrainButton' class='btn btn-primary mt-2'>Start Training with NFT</button>\n"
            "  </form>\n"

            "</div>\n"
            "```\n\n"

            # JS explanation
            "```javascript\n"
            "// 1) Local upload form setup\n"
            "function setupLocalTrainingForm() {\n"
            "  const form = document.getElementById('localTrainingForm');\n"
            "  if (!form) return;\n"
            "  form.onsubmit = function(e) {\n"
            "    e.preventDefault();\n"
            "    // Get character name and image file\n"
            "    const charName = document.getElementById('localCharName').value.trim();\n"
            "    const file = document.getElementById('localImageFile').files[0];\n"
            "    if (!charName || !file) {\n"
            "      alert('Please enter character name and select an image.');\n"
            "      return;\n"
            "    }\n"
            "    // TODO: Actual upload logic (FormData -> /api/upload_training_image/)\n"
            "  };\n"
            "}\n\n"

            "// 2) NFT search button setup\n"
            "function setupNftSearch() {\n"
            "  const btn = document.getElementById('nftSearchButton');\n"
            "  if (!btn) return;\n"
            "  btn.onclick = async function() {\n"
            "    const address = document.getElementById('nftWalletAddress').value.trim();\n"
            "    if (!address) {\n"
            "      alert('Please enter a wallet address');\n"
            "      return;\n"
            "    }\n"
            "    // fetch /api/fetch_nfts/ -> populate #nftSelect\n"
            "    // on success => document.getElementById('nftTrainingForm').style.display = 'block';\n"
            "  };\n"
            "}\n\n"

            "// 3) NFT training form submission\n"
            "function setupNftTrainingForm() {\n"
            "  const form = document.getElementById('nftTrainingForm');\n"
            "  if (!form) return;\n"
            "  form.onsubmit = function(e) {\n"
            "    e.preventDefault();\n"
            "    const select = document.getElementById('nftSelect');\n"
            "    const imageUrl = select.value;\n"
            "    const charName = document.getElementById('nftCharName').value.trim();\n"
            "    if (!imageUrl || !charName) {\n"
            "      alert('Please select an NFT image and enter character name.');\n"
            "      return;\n"
            "    }\n"
            "    // TODO: blob download => /api/upload_training_image/\n"
            "  };\n"
            "}\n\n"

            "// Execution\n"
            "function initTrainingForms() {\n"
            "  setupLocalTrainingForm();\n"
            "  setupNftSearch();\n"
            "  setupNftTrainingForm();\n"
            "}\n"
            "// initTrainingForms() should be called after forms are inserted into chat\n"
            "```"
        )
        return forms_html


    def _handle_nft_analysis(self, params: Dict[str, Any]) -> str:
        """
        Handle NFT analysis command with two modes:
        1. General market analysis
        2. Wallet-specific NFT analysis
        """
        try:
            address = params.get("address")
            
            if address:
                # Wallet-specific NFT analysis
                network = params.get("network", "arbitrum")
                nft_response = self.nft_service.get_nfts(address, network)
                
                if nft_response["status"] == "error":
                    return f"Error fetching NFTs: {nft_response['message']}"
                    
                if nft_response["status"] == "success":
                    nfts = nft_response["data"]["nfts"]
                    if not nfts:
                        return f"No NFTs found for address {address}"
                    return self._format_nft_response(nfts)
            else:
                # General market analysis
                return self.nft_service.process_nft_analysis()
                
        except Exception as e:
            logger.error(f"Error in NFT analysis: {str(e)}", exc_info=True)
            return f"Error analyzing NFTs: {str(e)}"