import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ITaskStore(ABC):
    @abstractmethod
    def save_task(self, task_id: str, data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

class ThreadSafeInMemoryTaskStore(ITaskStore):
    """
    Thread-safe in-memory store for development and single-process instances.
    Implements ITaskStore so it can be transparently swapped with RedisTaskStore.
    """
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save_task(self, task_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._store[task_id] = data

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._store.get(task_id)
            return task.copy() if task else None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if task_id in self._store:
                self._store[task_id].update(updates)
                return self._store[task_id].copy()
            return None
