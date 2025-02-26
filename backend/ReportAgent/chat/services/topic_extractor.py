# topic_extractor.py

import torch
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration

class TopicExtractor:
    """
    1) Generate a full caption from the image
    2) Also create a short topic from the caption
    """

    def __init__(self, model_path="/path/to/blip2", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[TopicExtractor] Loading model from '{model_path}' on {self.device}...")
        self.processor = Blip2Processor.from_pretrained(model_path, local_files_only=True)
        self.model = Blip2ForConditionalGeneration.from_pretrained(model_path, local_files_only=True)
        self.model.to(self.device)
        self.model.eval()

    def extract_caption_and_topic(self, image_path: str):
        """
        Return (full_caption, short_topic).
        - full_caption: e.g. "a cartoon character is standing in front of a city"
        - short_topic: e.g. "a_cartoon_character"
        """
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=30,
                do_sample=False,
                num_beams=5
            )
        full_caption = self.processor.tokenizer.decode(output_ids[0], skip_special_tokens=True)

        # 짧은 토픽: 첫 2~3단어만 사용
        words = full_caption.split()
        short_topic = "_".join(words[:3])
        # 불필요 문자 제거
        short_topic = ''.join(c for c in short_topic if c.isalnum() or c in {'_', '-'})
        if not short_topic:
            short_topic = "noTopic"

        return full_caption, short_topic
