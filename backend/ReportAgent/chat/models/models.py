import uuid 
from django.db import models
from datetime import datetime


class AgentModel(models.Model):
    """
    Represents an AI character model agent with a unique access key
    """
    agent_key = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: Add more fields as needed
    description = models.TextField(blank=True, null=True)
    prompt_template = models.TextField(blank=True, null=True, 
                                     help_text="Template for prompts to include character's style")
    
    class Meta:
        verbose_name = "AI Agent"
        verbose_name_plural = "AI Agents"
    
    def __str__(self):
        return f"{self.model_name} ({self.agent_key})"


class TrainingJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    character_name = models.CharField(max_length=100, unique=True)  # unique 제약 추가
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.FloatField(default=0.0)
    gpu_id = models.IntegerField(null=True)
    original_image = models.FileField(upload_to='original_images/')
    dataset_path = models.CharField(max_length=255) 
    processed_images_dir = models.CharField(max_length=255, null=True)
    config_path = models.CharField(max_length=255, null=True)
    error_message = models.TextField(null=True, blank=True)
    queue_position = models.IntegerField(null=True)
    estimated_time = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)
    task_id = models.CharField(max_length=8, null=True, unique=True)
    agent = models.OneToOneField(AgentModel, on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='training_job')
    def __str__(self):
        return f"{self.character_name} - {self.status} ({self.progress:.1f}%)"

    def update_progress(self, progress: float, status: str = None):
        self.progress = progress
        if status:
            self.status = status
        if status == 'completed':
            self.completed_at = datetime.now()
        self.save()

    def log_error(self, error_message: str):
        self.error_message = error_message
        self.status = 'failed'
        self.save()


class TrainingLog(models.Model):
    job = models.ForeignKey(TrainingJob, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    level = models.CharField(max_length=20, default='info')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: {self.message[:50]}..."