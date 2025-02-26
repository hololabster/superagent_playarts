from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    # 기존 뷰
    chat_view, 
    send_message, 
    upload_training_image, 
    check_training_status,
    fetch_nfts,
    twit_view,
    
    # 에이전트 뷰 (views.py 파일에 추가된 새 함수들)
    agent_inference,
    model_inference,
    get_image,
    list_agents,
    list_models,
    reload_models
)

urlpatterns = [
    # 기존 URL 패턴
    path('', chat_view, name='chat'),
    path('api/send_message/', send_message, name='send_message'),
    path('api/upload_training_image/', upload_training_image, name='upload_training_image'),
    path('api/check_training_status/', check_training_status, name='check_training_status'),
    path('api/fetch_nfts/', fetch_nfts, name='fetch_nfts'),
    
    # Agent API endpoints
    path('agent/<uuid:agent_key>/inference', agent_inference, name='agent_inference'),
    path('model/<str:model_name>/inference', model_inference, name='model_inference'),
    path('images/<str:image_id>', get_image, name='get_image'),
    path('list_agents', list_agents, name='list_agents'),
    path('list_models', list_models, name='list_models'),
    path('reload_models', reload_models, name='reload_models'),
    path('twit', twit_view, name='twit_view'),
]

# 정적 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # 프로덕션 환경에서도 미디어 파일을 Django로 제공
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)