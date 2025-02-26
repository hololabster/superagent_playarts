from django.contrib import admin
from .models import TrainingJob, TrainingLog

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'character_name', 'status', 'progress', 'gpu_id', 
                   'queue_position', 'created_at', 'updated_at')
    list_filter = ('status', 'gpu_id')
    search_fields = ('character_name', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('logs')

@admin.register(TrainingLog)
class TrainingLogAdmin(admin.ModelAdmin):
    list_display = ('job', 'timestamp', 'level', 'message')
    list_filter = ('level', 'timestamp')
    search_fields = ('message',)
    raw_id_fields = ('job',)