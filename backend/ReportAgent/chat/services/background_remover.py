#universal_background_remover.py
import torch
import numpy as np
from PIL import Image
import cv2
from segment_anything import sam_model_registry, SamPredictor
from typing import Optional, Tuple

class UniversalBackgroundRemover:
    def __init__(self, 
                 sam_checkpoint: str = "sam_vit_h_4b8939.pth",
                 model_type: str = "vit_h",
                 device: Optional[str] = None):
        """
        Initialize the background remover with SAM model
        Args:
            sam_checkpoint: Path to the SAM model checkpoint
            model_type: Type of SAM model (vit_h, vit_l, vit_b)
            device: Device to run the model on
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize SAM
        sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
        sam.to(device=self.device)
        self.predictor = SamPredictor(sam)

    def _generate_prompts(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate automatic prompts for the image
        Args:
            image: Input image in numpy array format
        Returns:
            point_coords: Coordinates for point prompts
            point_labels: Labels for point prompts (1 for foreground, 0 for background)
        """
        # Convert to grayscale for processing
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Find the center of mass of the image
        moments = cv2.moments(gray)
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = image.shape[1]//2, image.shape[0]//2

        # Generate foreground points
        point_coords = np.array([[cx, cy]])  # Center point
        point_labels = np.array([1])  # 1 for foreground

        # Add background points at corners
        h, w = image.shape[:2]
        bg_points = np.array([
            [0, 0],  # Top-left
            [w-1, 0],  # Top-right
            [0, h-1],  # Bottom-left
            [w-1, h-1]  # Bottom-right
        ])
        point_coords = np.concatenate([point_coords, bg_points])
        point_labels = np.concatenate([point_labels, np.zeros(4)])  # 0 for background

        return point_coords, point_labels

    def _refine_mask(self, 
                    mask: np.ndarray, 
                    image: np.ndarray,
                    effect_preservation: float = 0.5) -> np.ndarray:
        """
        Refine the segmentation mask with special handling for effects
        Args:
            mask: Binary segmentation mask
            image: Original image
            effect_preservation: Strength of effect preservation (0-1)
        Returns:
            Refined mask
        """
        # Convert image to LAB color space for better color analysis
        lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        
        # Calculate color difference from center to detect effects
        h, w = image.shape[:2]
        center_color = lab_image[h//2, w//2]
        color_diff = np.sqrt(np.sum((lab_image - center_color)**2, axis=2))
        
        # Normalize color difference
        color_diff = (color_diff - color_diff.min()) / (color_diff.max() - color_diff.min())
        
        # Create effect mask
        effect_mask = color_diff > (1 - effect_preservation)
        
        # Calculate kernel size (ensure it's odd)
        kernel_size = max(3, int(min(h, w) * 0.01))
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Dilate the original mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated_mask = cv2.dilate(mask.astype(np.uint8), kernel)
        
        # Combine masks with smooth transition
        combined_mask = cv2.addWeighted(
            dilated_mask, 1 - effect_preservation,
            effect_mask.astype(np.uint8), effect_preservation,
            0
        )
        
        # Apply gaussian blur for smooth edges (ensure kernel size is odd)
        refined_mask = cv2.GaussianBlur(combined_mask, (kernel_size, kernel_size), 0)
        
        return refined_mask

    def remove_background(self, 
                         image_path: str, 
                         output_path: str,
                         effect_preservation: float = 0.5) -> None:
        """
        Remove background from image while preserving effects
        Args:
            image_path: Path to input image
            output_path: Path to save output image
            effect_preservation: Strength of effect preservation (0-1)
        """
        # Load image
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Set image in predictor
        self.predictor.set_image(image)
        
        # Generate and set prompts
        point_coords, point_labels = self._generate_prompts(image)
        
        # Get masks
        masks, scores, _ = self.predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True
        )
        
        # Select best mask
        best_mask = masks[scores.argmax()]
        
        # Refine mask
        refined_mask = self._refine_mask(best_mask, image, effect_preservation)
        
        # Apply mask to image
        result = np.dstack([image, refined_mask * 255])
        
        # Save result
        result_image = Image.fromarray(result.astype(np.uint8))
        result_image.save(output_path, format='PNG')

def _remove_background(self, source_image_path: str, out_path: str):
    """
    Enhanced background removal using SAM with universal compatibility
    """
    remover = UniversalBackgroundRemover(
        sam_checkpoint="/path/to/sam_vit_h_4b8939.pth"
    )
    # Detect if image is illustration/anime or photo
    img = Image.open(source_image_path)
    img_array = np.array(img)
    
    # Calculate image statistics for style detection
    edge_density = cv2.Canny(img_array, 100, 200).mean()
    color_variance = img_array.std(axis=(0,1)).mean()
    
    # Adjust effect preservation based on image style
    if edge_density > 50 and color_variance < 60:  # Likely illustration/anime
        effect_preservation = 0.7
    else:  # Likely photo
        effect_preservation = 0.3
        
    remover.remove_background(
        source_image_path, 
        out_path, 
        effect_preservation=effect_preservation
    )