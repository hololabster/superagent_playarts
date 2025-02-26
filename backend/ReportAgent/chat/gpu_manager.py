from queue import Queue
from threading import Lock
from datetime import datetime
from ...models.models import TrainingJob
import logging

logger = logging.getLogger(__name__)

class GPUManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        """초기화 로직"""
        self.available_gpus = [0, 4, 7]  # 사용 가능한 GPU IDs
        self.gpu_locks = {gpu: Lock() for gpu in self.available_gpus}
        self.training_queue = Queue()
        self.active_trainings = {}  # gpu_id: job_id mapping
        
        # 서버 재시작 시 이전 작업 상태 복구
        self._recover_previous_state()

    def _recover_previous_state(self):
        """서버 재시작 시 이전 작업 상태 복구"""
        try:
            # running 상태의 작업들을 queued로 변경
            running_jobs = TrainingJob.objects.filter(status='running')
            for job in running_jobs:
                logger.info(f"Recovering job {job.id}: {job.character_name}")
                job.status = 'queued'
                job.gpu_id = None
                job.save()
                self.add_to_queue(job.id)
            
            # queued 상태의 작업들을 큐에 다시 추가
            queued_jobs = TrainingJob.objects.filter(status='queued')
            for job in queued_jobs:
                if job.id not in self.training_queue.queue:
                    self.add_to_queue(job.id)
                    
        except Exception as e:
            logger.error(f"Error recovering previous state: {str(e)}")

    def get_available_gpu(self) -> int:
        """사용 가능한 GPU를 찾아 반환"""
        for gpu_id in self.available_gpus:
            if gpu_id not in self.active_trainings:
                return gpu_id
        return None

    def assign_gpu(self, job_id: int) -> int:
        """작업에 GPU 할당"""
        gpu_id = self.get_available_gpu()
        if gpu_id is not None:
            try:
                job = TrainingJob.objects.get(id=job_id)
                self.active_trainings[gpu_id] = job_id
                job.gpu_id = gpu_id
                job.status = 'running'
                job.save()
                logger.info(f"Assigned GPU {gpu_id} to job {job_id}")
                return gpu_id
            except Exception as e:
                logger.error(f"Error assigning GPU: {str(e)}")
                return None
        return None

    def release_gpu(self, gpu_id: int):
        """GPU 반환"""
        if gpu_id in self.active_trainings:
            job_id = self.active_trainings[gpu_id]
            try:
                job = TrainingJob.objects.get(id=job_id)
                job.gpu_id = None
                if job.status != 'completed':
                    job.status = 'failed'
                job.save()
            except TrainingJob.DoesNotExist:
                pass
            del self.active_trainings[gpu_id]
            logger.info(f"Released GPU {gpu_id}")

    def add_to_queue(self, job_id: int):
        """작업을 큐에 추가"""
        if job_id not in self.training_queue.queue:
            self.training_queue.put(job_id)
            try:
                job = TrainingJob.objects.get(id=job_id)
                job.status = 'queued'
                job.queue_position = self.training_queue.qsize()
                job.save()
                logger.info(f"Added job {job_id} to queue. Position: {job.queue_position}")
            except Exception as e:
                logger.error(f"Error adding job to queue: {str(e)}")

    def get_next_job(self) -> int:
        """큐에서 다음 작업 가져오기"""
        if not self.training_queue.empty():
            return self.training_queue.get()
        return None

    def get_queue_status(self) -> dict:
        """현재 큐 상태 반환"""
        queue_size = self.training_queue.qsize()
        active_count = len(self.active_trainings)
        available_count = len(self.available_gpus) - active_count
        
        # 활성 작업 정보 수집
        active_jobs = []
        for gpu_id, job_id in self.active_trainings.items():
            try:
                job = TrainingJob.objects.get(id=job_id)
                active_jobs.append({
                    'job_id': job_id,
                    'character_name': job.character_name,
                    'progress': job.progress,
                    'gpu_id': gpu_id
                })
            except TrainingJob.DoesNotExist:
                continue
        
        return {
            'queue_size': queue_size,
            'active_trainings': active_jobs,
            'available_gpus': available_count,
            'total_gpus': len(self.available_gpus)
        }

    def update_queue_positions(self):
        """큐의 모든 작업 위치 업데이트"""
        # 큐에 있는 작업 ID 목록 가져오기
        queue_items = list(self.training_queue.queue)
        
        # 각 작업의 위치 업데이트
        for position, job_id in enumerate(queue_items, 1):
            try:
                job = TrainingJob.objects.get(id=job_id)
                job.queue_position = position
                job.save()
            except TrainingJob.DoesNotExist:
                continue