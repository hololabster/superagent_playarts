import torch
from diffusers import FluxPipeline
from PIL import Image
import uuid
import os
import logging
import threading
from django.conf import settings
# Import PEFT libraries
from peft import PeftModel, PeftConfig
import transformers

logger = logging.getLogger(__name__)
# Singleton instance
model_manager_instance = None
instance_lock = threading.Lock()

def get_model_manager():
    """
    Get or create the singleton instance of ModelManager
    """
    global model_manager_instance
    if model_manager_instance is None:
        with instance_lock:
            if model_manager_instance is None:
                # Default to GPU 7
                gpu_id = getattr(settings, 'AI_GPU_ID', 7)
                model_manager_instance = ModelManager(gpu_id)
    return model_manager_instance

class ModelManager:
    """
    Manages the Flux model and LoRA weights for character generation
    """
    def __init__(self, gpu_id=7, base_dir=None):
        self.device = torch.device(f'cuda:{gpu_id}' if torch.cuda.is_available() else 'cpu')
        logger.info(f"ModelManager initializing with device: {self.device}")
        
        # Base model path
        self.base_model_path = "black-forest-labs/FLUX.1-schnell"
        
        # Base directory for model outputs
        self.base_dir = base_dir or os.path.join(
            getattr(settings, 'AI_TOOLKIT_ROOT', '/mnt/striped_nvme/ai-toolkit'), 
            'output'
        )
        
        # Store mapping of model names to lora weight files
        self.lora_weights = {}
        
        # Current loaded model
        self.current_model = None
        
        # Initialize pipeline
        self._initialize_pipeline()
        
        # Discover available models
        self.preload_all_lora_weights(self.base_dir)
        
        logger.info(f"ModelManager initialized with {len(self.lora_weights)} models")
    
    def _initialize_pipeline(self):
        """Initialize the Flux pipeline"""
        try:
            # Ensure transformers and peft libraries are properly loaded
            logger.info(f"Transformers version: {transformers.__version__}")
            logger.info("Loading base model from {self.base_model_path}")
            
            # Make sure we're loading with proper PEFT support
            self.pipeline = FluxPipeline.from_pretrained(
                self.base_model_path,
                torch_dtype=torch.float16,
                use_peft=True  # Explicitly enable PEFT support
            )
            self.pipeline.to(self.device)
            logger.info("Base model loaded successfully")
        except Exception as e:
            logger.error(f"Error initializing Flux pipeline: {e}")
            raise
    
    def preload_all_lora_weights(self, base_dir):
        """
        Discover and map all available LoRA weight files
        """
        if not os.path.exists(base_dir):
            logger.warning(f"Base directory does not exist: {base_dir}")
            return
        try:
            count = 0
            for folder_name in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, folder_name)
                if os.path.isdir(folder_path):
                    for file_name in os.listdir(folder_path):
                        if file_name.endswith("_flux_lora_v1.safetensors"):
                            model_name = folder_name.replace("_flux_lora_v1", "")
                            self.lora_weights[model_name] = os.path.join(folder_path, file_name)
                            count += 1
                            logger.info(f"Discovered LoRA weights for model: {model_name} at {self.lora_weights[model_name]}")
            
            logger.info(f"Total models discovered: {count}")
        except Exception as e:
            logger.error(f"Error preloading LoRA weights: {e}")
    
    def load_lora_weights(self, model_name):
        """
        Load specific LoRA weights for a model
        """
        try:
            # If requesting the base model, just unload any current LoRA
            if model_name == 'base':
                if self.current_model != 'base' and hasattr(self.pipeline, 'unload_lora_weights'):
                    logger.info("Unloading any existing LoRA weights")
                    self.pipeline.unload_lora_weights()
                    torch.cuda.empty_cache()
                self.current_model = 'base'
                return True
    
            # Check if model exists
            if model_name not in self.lora_weights:
                logger.error(f"LoRA weights for {model_name} not found")
                return False
            
            # Skip loading if same model is already loaded
            if model_name == self.current_model:
                logger.info(f"Model {model_name} already loaded")
                return True
            
            # Unload any existing LoRA weights
            if hasattr(self.pipeline, 'unload_lora_weights'):
                logger.info("Unloading any existing LoRA weights")
                self.pipeline.unload_lora_weights()
                torch.cuda.empty_cache()
            
            # Load new LoRA weights with proper PEFT backend
            logger.info(f"Loading LoRA weights for {model_name}: {self.lora_weights[model_name]}")
            
            # Try to ensure PEFT is properly initialized
            try:
                # Import PEFT's PeftModel specifically for LoRA
                from peft import LoraConfig
                
                # Log PEFT version
                import peft
                logger.info(f"PEFT version: {peft.__version__}")
                
                self.pipeline.load_lora_weights(self.lora_weights[model_name])
                
            except ImportError:
                logger.error("PEFT library not properly installed. Install with 'pip install peft'")
                return False
            except Exception as peft_error:
                logger.error(f"PEFT error: {peft_error}")
                return False
                
            self.current_model = model_name
            return True
    
        except Exception as e:
            logger.error(f"Error loading LoRA weights for {model_name}: {e}")
            torch.cuda.empty_cache()
            return False

    def generate_image(self, model_name, prompt, aspect_ratio='square', seed=42):
        """
        Generate an image using the specified model
        """
        try:
            # Ensure the right model is loaded
            if not self.load_lora_weights(model_name):
                return {
                    "status": "error",
                    "message": f"Failed to load model: {model_name}"
                }
            
            # Define dimensions based on aspect ratio
            aspect_ratio_dimensions = {
                'square': (768, 768),
                'portrait': (768, 1024),
                'standard': (1024, 768),
                'widescreen': (1024, 576)
            }
            
            height, width = aspect_ratio_dimensions.get(aspect_ratio, (768, 768))
            
            # Set up generator with seed
            generator = torch.Generator(device=self.device).manual_seed(seed)
            
            logger.info(f"Generating image with model {model_name}, prompt: {prompt[:50]}...")
            
            # Generate the image
            with torch.no_grad():
                output = self.pipeline(
                    prompt,
                    num_inference_steps=15,
                    guidance_scale=0.9,
                    generator=generator,
                    height=height,
                    width=width,
                )
            
            # Save the image
            output_dir = os.path.join(settings.MEDIA_ROOT, "generated_images")
            os.makedirs(output_dir, exist_ok=True)
            
            image_id = str(uuid.uuid4())
            file_name = f'{image_id}.png'
            file_path = os.path.join(output_dir, file_name)
            
            output.images[0].save(file_path)
            logger.info(f"Image saved at: {file_path}")
            
            # Clean up
            del generator
            del output.images
            del output
            torch.cuda.empty_cache()
            
            # Return image info
            return {
                "status": "success",
                "image_id": image_id,
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            torch.cuda.empty_cache()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_available_models(self):
        """Return a list of all available models"""
        return list(self.lora_weights.keys())
    
    def reload_models(self):
        """Reload the list of available models"""
        self.lora_weights = {}
        self.preload_all_lora_weights(self.base_dir)
        return len(self.lora_weights)