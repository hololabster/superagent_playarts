# views.py (전체 예시)
import os
import json
import traceback
import logging
import uuid
import shutil
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
import json
from dotenv import load_dotenv  # python-dotenv 라이브러리 import
import random
# .env 파일 로드
load_dotenv()  # 이 라인을 추가하여 .env 파일의 환경 변수를 로드합니다

from .core.orchestrator import CommandOrchestrator
from .services.trainer_service import TrainerService
from .services.nft_service import NFTService
from .models import AgentModel, TrainingJob
from .services.model_manager import get_model_manager

logger = logging.getLogger(__name__)

# Orchestrator: LLM 명령 파이프라인
orchestrator = CommandOrchestrator()

# Services
trainer_service = TrainerService()
nft_service = NFTService()

def chat_view(request):
    return render(request, 'chat/index.html')

@csrf_exempt
def send_message(request):
    """
    단순히 LLM Orchestrator에 메시지를 전달하여 
    응답을 JSON 형태로 반환
    """
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            
            # LLM과의 상호작용
            response_text = orchestrator.process_input(message)

            return JsonResponse({
                'status': 'success',
                'response': response_text,
                'length': len(response_text)
            })
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return JsonResponse({
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def fetch_nfts(request):
    """
    지갑 주소로부터 NFT 목록을 조회해 
    [ { "token_id", "name", "image_url" }, ... ] 형태로 반환
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            address = data.get('address')
            if not address:
                return JsonResponse({'error': 'Missing address'}, status=400)

            # ✅ NFT 정보 가져오기
            nft_response = nft_service.get_nfts(address, "arbitrum")

            if nft_response["status"] == "success":
                nfts = nft_response["data"]["nfts"]
                formatted_nfts = []
                
                for nft in nfts:
                    token_uri = nft.get("token_uri", "")  # ✅ `tokenURI`가 있는지 확인
                    image_url = nft.get("image_url", "").strip()  # 기본 image_url
                    
                    # ✅ tokenURI에서 직접 메타데이터 조회
                    if not image_url and token_uri:
                        image_url = nft_service.get_image_url_from_token_uri(token_uri)

                    nft_data = {
                        'token_id': nft.get('token_id', 'N/A'),
                        'name': nft.get('name', f'NFT #{nft.get("token_id", "Unknown")}'),
                        'image_url': image_url,
                        'token_uri': token_uri
                    }
                    formatted_nfts.append(nft_data)

                return JsonResponse({
                    'status': 'success',
                    'nfts': formatted_nfts
                })
            else:
                return JsonResponse(nft_response, status=400)

        except Exception as e:
            logger.error(f"Error in fetch_nfts: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def upload_training_image(request):
    if request.method == 'POST':
        character_name = request.POST.get('character_name', '').strip()
        if not character_name:
            return HttpResponseBadRequest("Missing character_name")
        
        # Check if character name already exists
        dataset_path = os.path.join(settings.MEDIA_ROOT, f"{character_name}_dataset")
        if os.path.exists(dataset_path):
            return JsonResponse({
                'status': 'error',
                'message': f'Character name "{character_name}" is already in use. Please choose a different name.'
            }, status=400)
        
        if TrainingJob.objects.filter(character_name=character_name).exists():
            return JsonResponse({
                'status': 'error',
                'message': f'Character name "{character_name}" is already registered in our database. Please choose a different name.'
            }, status=400)
        
        uploaded_file = request.FILES.get('character_image')
        if not uploaded_file:
            return HttpResponseBadRequest("No file uploaded")

        try:
            # Save the uploaded file
            upload_dir = os.path.join(settings.MEDIA_ROOT, "training_uploads", character_name)
            os.makedirs(upload_dir, exist_ok=True)
            
            unique_id = str(uuid.uuid4())[:8]
            file_ext = os.path.splitext(uploaded_file.name)[1]
            filename = f"{character_name}_{unique_id}{file_ext}"
            saved_file_path = os.path.join(upload_dir, filename)
            
            with open(saved_file_path, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Generate an absolute URL for external access
            # 서버의 도메인과 프로토콜을 포함한 완전한 URL 생성
            domain = "https://api-ai-agent.playarts.ai"  # 서버의 실제 도메인이나 IP 주소로 변경
            relative_path = f"training_uploads/{character_name}/{filename}"
            media_url = f"{domain}{settings.MEDIA_URL}{relative_path}"
            
            # Create training job
            training_job = TrainingJob.objects.create(
                character_name=character_name,
                dataset_path=dataset_path,
                original_image=saved_file_path,
                status='pending'
            )

            # Start the LoRA training job
            task_id = trainer_service.start_lora_training(character_name, saved_file_path)
            
            # Update job with task ID
            training_job.task_id = task_id
            training_job.status = 'queued'
            training_job.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Training started for character "{character_name}"',
                'task_id': task_id,
                'media_url': media_url  # 외부에서 접근 가능한 절대 URL
            })
            
        except Exception as e:
            # Clean up if something goes wrong
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return HttpResponseBadRequest("Invalid method")

@csrf_exempt
def check_training_status(request):
    """
    클라이언트가 5초 간격으로 학습 로그/상태를 폴링
    """
    task_id = request.GET.get('task_id')
    if not task_id:
        return HttpResponseBadRequest("Missing task_id")
    
    logs_output = trainer_service.get_logs(task_id)
    
    # DB에서 job status 가져오기
    try:
        job = TrainingJob.objects.get(task_id=task_id)
        status_info = {
            "progress": job.progress,
            "status": job.status,
            "queue_position": job.queue_position,
            "estimated_time": job.estimated_time
        }
    except TrainingJob.DoesNotExist:
        status_info = {}

    return JsonResponse({
        "status": "success",
        "task_id": task_id,
        "logs": logs_output,
        "job_status": status_info
    })

logger = logging.getLogger(__name__)

@csrf_exempt
def agent_inference(request, agent_key):
    """Generate image using a specific agent key"""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"}, status=405)
    
    try:
        # Find the agent by key
        try:
            agent = AgentModel.objects.get(agent_key=agent_key)
        except AgentModel.DoesNotExist:
            return JsonResponse({
                "status": "error", 
                "message": f"No agent found with key {agent_key}"
            }, status=404)
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "error", 
                "message": "Invalid JSON in request body"
            }, status=400)
        
        # Extract parameters
        prompt = data.get('prompt', '')
        aspect_ratio = data.get('aspect_ratio', 'square')
        seed = data.get('seed', 42)
        
        if not prompt:
            return JsonResponse({
                "status": "error", 
                "message": "Prompt is required"
            }, status=400)
        
        # Get model manager
        model_manager = get_model_manager()
        
        # Generate image
        result = model_manager.generate_image(agent.model_name, prompt, aspect_ratio, seed)
        
        if result['status'] == 'success':
            # Create URL for the image
            image_url = f"/media/generated_images/{result['image_id']}.png"
            
            # Update response with full URL
            domain = "https://api-ai-agent.playarts.ai"
            full_url = f"{domain}{image_url}"
            
            return JsonResponse({
                "status": "success",
                "image_id": result['image_id'],
                "file_path": result['file_path'],
                "image_url": full_url
            })
        else:
            return JsonResponse(result, status=500)
            
    except Exception as e:
        logger.error(f"Error in agent_inference: {e}", exc_info=True)
        return JsonResponse({
            "status": "error", 
            "message": f"Internal server error: {str(e)}"
        }, status=500)

@csrf_exempt
def model_inference(request, model_name):
    """Generate image using a model name directly"""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"}, status=405)
    
    try:
        # Get model manager
        model_manager = get_model_manager()
        
        # Check if model exists
        available_models = model_manager.get_available_models()
        if model_name not in available_models:
            return JsonResponse({
                "status": "error", 
                "message": f"Model {model_name} not found. Available models: {available_models}"
            }, status=404)
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "error", 
                "message": "Invalid JSON in request body"
            }, status=400)
        
        # Extract parameters
        prompt = data.get('prompt', '')
        aspect_ratio = data.get('aspect_ratio', 'square')
        seed = data.get('seed', 42)
        
        if not prompt:
            return JsonResponse({
                "status": "error", 
                "message": "Prompt is required"
            }, status=400)
        
        # Generate image
        result = model_manager.generate_image(model_name, prompt, aspect_ratio, seed)
        
        if result['status'] == 'success':
            # Create URL for the image
            image_url = f"/media/generated_images/{result['image_id']}.png"
            
            # Update response with full URL
            domain = "https://api-ai-agent.playarts.ai"
            full_url = f"{domain}{image_url}"
            
            return JsonResponse({
                "status": "success",
                "image_id": result['image_id'],
                "file_path": result['file_path'],
                "image_url": full_url
            })
        else:
            return JsonResponse(result, status=500)
            
    except Exception as e:
        logger.error(f"Error in model_inference: {e}", exc_info=True)
        return JsonResponse({
            "status": "error", 
            "message": f"Internal server error: {str(e)}"
        }, status=500)

def get_image(request, image_id):
    """Return a generated image by ID"""
    try:
        # Construct file path
        file_path = os.path.join(settings.MEDIA_ROOT, "generated_images", f"{image_id}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            return HttpResponse(f"Image {image_id} not found", status=404)
        
        # Return the image file
        return FileResponse(open(file_path, 'rb'), content_type='image/png')
        
    except Exception as e:
        logger.error(f"Error returning image: {e}", exc_info=True)
        return HttpResponse(f"Error retrieving image: {str(e)}", status=500)

def list_agents(request):
    """List all available agents"""
    try:
        agents = AgentModel.objects.all().values('agent_key', 'model_name', 'created_at')
        return JsonResponse({
            "status": "success",
            "agents": list(agents)
        })
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        return JsonResponse({
            "status": "error", 
            "message": f"Error listing agents: {str(e)}"
        }, status=500)

def list_models(request):
    """List all available models"""
    try:
        model_manager = get_model_manager()
        models = model_manager.get_available_models()
        return JsonResponse({
            "status": "success",
            "models": models
        })
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JsonResponse({
            "status": "error", 
            "message": f"Error listing models: {str(e)}"
        }, status=500)

def reload_models(request):
    """Reload the list of available models"""
    try:
        model_manager = get_model_manager()
        count = model_manager.reload_models()
        return JsonResponse({
            "status": "success",
            "message": f"Successfully reloaded {count} models"
        })
    except Exception as e:
        logger.error(f"Error reloading models: {e}", exc_info=True)
        return JsonResponse({
            "status": "error", 
            "message": f"Error reloading models: {str(e)}"
        }, status=500)

@csrf_exempt
def twit_view(request):
    """
    Twitter analysis endpoint: Analyze text and generate character images based on the situation
    
    Request format: {
        "agentKey": "agent_key(uuid)",
        "characterName": "filter_trigger_name",
        "targetMessage": "text_message",
        "handle": "twitter_handle"
    }
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST method is allowed"}, status=405)
    
    try:
        # Parse JSON request
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ["agentKey", "characterName", "targetMessage", "handle"]
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    "status": "error", 
                    "message": f"Missing required field: {field}"
                }, status=400)
        
        agent_key = data["agentKey"]
        character_name = data["characterName"]
        target_message = data["targetMessage"]
        handle = data["handle"]
        
        logger.info(f"Received Twitter analysis request from @{handle}: {target_message[:50]}...")
        
        # Validate agent key
        try:
            agent = AgentModel.objects.get(agent_key=agent_key)
        except AgentModel.DoesNotExist:
            return JsonResponse({
                "status": "error", 
                "message": f"Invalid agent key: {agent_key}"
            }, status=404)
        
        # Use LLM to analyze the situation and generate prompt and response
        from .services.llm_service import LLMService
        llm_service = LLMService()
        
        # Construct LLM prompt template for situation analysis
        prompt_template = f"""
        You are Takoyan_AI, a sassy AI character who responds to Twitter users. Analyze the following message from @{handle}:

        Message: "{target_message}"

        First, analyze the situation described in the message. If someone clearly made a mistake or acted inappropriately in the situation, feel free to be sarcastic or slightly mocking in your analysis.

        Then, suggest an appropriate image prompt that visualizes this situation using the {character_name} art style.

        Please respond in the following format:
        1. Situation analysis and witty response (1-3 sentences, can be sarcastic if warranted)
        2. Detailed image generation prompt (in English, detailed, maximum 100 words)

        Provide the results in JSON format:
        {{
          "twitter_response": "Your witty analysis and response",
          "image_prompt": "Detailed image generation prompt in English"
        }}
        """
        
        # Generate LLM response
        llm_response = llm_service.generate_llm_response(prompt_template)
        
        if not llm_response:
            return JsonResponse({
                "status": "error",
                "message": "Failed to generate analysis and prompt"
            }, status=500)
        
        # Extract JSON from LLM response
        try:
            import re
            json_match = re.search(r'({[\s\S]*})', llm_response)
            
            if json_match:
                result = json.loads(json_match.group(1))
                twitter_response = result.get("twitter_response", "")
                image_prompt = result.get("image_prompt", "")
            else:
                # Handle non-JSON response by parsing text
                lines = llm_response.strip().split('\n')
                twitter_response = next((line for line in lines if line.startswith("1.")), "").replace("1.", "").strip()
                image_prompt = next((line for line in lines if line.startswith("2.")), "").replace("2.", "").strip()
                
                if not twitter_response or not image_prompt:
                    # Try alternate parsing method
                    parts = llm_response.split("\n\n")
                    if len(parts) >= 2:
                        twitter_response = parts[0].strip()
                        image_prompt = parts[1].strip()
            
            # Ensure we have both required outputs
            if not twitter_response or not image_prompt:
                raise ValueError("Failed to extract both twitter_response and image_prompt from LLM output")
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Error parsing LLM response: {str(e)}"
            }, status=500)
        
        # Generate image using ModelManager
        try:
            model_manager = get_model_manager()
            
            # Check if character model is available
            available_models = model_manager.get_available_models()
            if character_name not in available_models:
                logger.warning(f"Character model '{character_name}' not found. Available models: {available_models}")
                
                # Try to find a close match
                close_match = next((model for model in available_models if character_name.lower() in model.lower()), None)
                if close_match:
                    logger.info(f"Using close match '{close_match}' instead of '{character_name}'")
                    character_name = close_match
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": f"Character model '{character_name}' not found and no suitable alternative found"
                    }, status=404)
            
            # Generate the image
            image_result = model_manager.generate_image(
                model_name=character_name,
                prompt=image_prompt,
                aspect_ratio="square",
                seed=random.randint(1, 9999)
            )
            
            if image_result["status"] != "success":
                return JsonResponse({
                    "status": "error",
                    "message": f"Image generation failed: {image_result.get('message', 'Unknown error')}"
                }, status=500)
            
            # Get the image URL and file path
            domain = "https://api-ai-agent.playarts.ai"
            image_url = f"{domain}/media/generated_images/{image_result['image_id']}.png"
            image_path = image_result['file_path']
            
            # Post to Twitter using the Twitter API
            import os
            import tweepy
            
            # Get Twitter API credentials from environment variables
            TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
            CONSUMER_KEY = os.getenv("TWITTER_API_KEY")
            CONSUMER_SECRET = os.getenv("TWITTER_API_SECRET")
            ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
            ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
            
            # Format tweet text
            tweet_text = f"@{handle} {twitter_response}"
            
            # Check tweet length and truncate if necessary (Twitter limit is 280 chars)
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."
                
            try:
                # Initialize the Twitter client
                client = tweepy.Client(
                    bearer_token=TWITTER_BEARER_TOKEN,
                    consumer_key=CONSUMER_KEY, 
                    consumer_secret=CONSUMER_SECRET,
                    access_token=ACCESS_TOKEN, 
                    access_token_secret=ACCESS_TOKEN_SECRET
                )
                
                # For uploading media, we need to use the API v1.1
                auth = tweepy.OAuth1UserHandler(
                    CONSUMER_KEY, CONSUMER_SECRET,
                    ACCESS_TOKEN, ACCESS_TOKEN_SECRET
                )
                api = tweepy.API(auth)
                
                # Upload the image
                media = api.media_upload(image_path)
                
                # Post the tweet with the image
                response = client.create_tweet(
                    text=tweet_text,
                    media_ids=[media.media_id]
                )
                
                # Extract tweet ID from response
                tweet_id = response.data['id']
                twitter_url = f"https://twitter.com/user/status/{tweet_id}"
                
                logger.info(f"Successfully posted to Twitter: {twitter_url}")
                
            except Exception as twitter_error:
                logger.error(f"Error posting to Twitter: {str(twitter_error)}")
                return JsonResponse({
                    "status": "error",
                    "message": f"Error posting to Twitter: {str(twitter_error)}"
                }, status=500)
            
            # Return success response with Twitter URL
            return JsonResponse({
                "response": "success",
                "twitterUrl": twitter_url,
                "imageUrl": image_url
            })
            
        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return JsonResponse({
                "status": "error",
                "message": f"Error generating image: {str(e)}"
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        logger.error(f"Error in twit_view: {e}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }, status=500)