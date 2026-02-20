from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict


class BaseProvider(ABC):
    @abstractmethod
    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    async def chat_completions_stream(
        self, payload: Dict[str, Any]
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def list_models(self) -> Dict[str, Any]:
        """获取模型列表

        Returns:
            Dict containing model list with format:
            {
                "object": "list",
                "data": [
                    {
                        "id": "model-id",
                        "object": "model",
                        "created": timestamp,
                        "owned_by": "organization"
                    }
                ]
            }
        """
        ...
