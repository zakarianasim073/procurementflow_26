import io

import pytest
from fastapi import UploadFile

from app.services.file_upload_service import FileUploadService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tender_id", "doc_type"),
    [
        (r"..\..\escaped", "boq"),
        ("safe-tender", r"..\..\escaped"),
    ],
)
async def test_document_upload_rejects_path_traversal(tender_id, doc_type):
    upload = UploadFile(
        filename="boq.pdf",
        file=io.BytesIO(b"%PDF-1.4"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(Exception, match="Invalid (tender_id|doc_type)"):
        await FileUploadService.upload_document(
            upload,
            tender_id=tender_id,
            doc_type=doc_type,
            tenant_id="tenant-1",
        )
