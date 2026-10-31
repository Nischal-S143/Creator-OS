"""Local file storage for development. An S3 adapter with the same methods replaces it for deployment."""

import uuid
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, root: Path):
        self._root = root

    def save_brand_document(
        self, organization_id: uuid.UUID, brand_id: uuid.UUID, document_id: uuid.UUID, ext: str, data: bytes
    ) -> str:
        # Built only from server-side ids and an allowlisted extension, never from the uploaded name.
        key = f"organizations/{organization_id}/brands/{brand_id}/documents/{document_id}{ext}"
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key


@lru_cache
def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().upload_dir)
