from fastapi import APIRouter, Request, Response
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.strategies import PartitionStrategy
from pydantic import BaseModel
import logging
from typing import List, Optional
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/extract",
    tags=["extract"],
    responses={404: {"description": "Not found"}},
)

class ExtractedElement(BaseModel):
    id: str
    is_html: bool
    text: str
    page_number: Optional[int] = None
    file_name: str

@router.post("/extract/{name}")
async def extract(request: Request, name:str)->List[ExtractedElement]:
    elements = partition_pdf(name, include_page_breaks=True, infer_table_structure=True, strategy=PartitionStrategy.HI_RES)
    extracted_elements = [0]*len(elements)
    logger.warning(f"{len(elements)} elements found")
    for i in range(len(elements)):
        text = elements[i].text
        is_html = False
        page_number = None
        if elements[i].metadata.text_as_html:
            text = elements[i].metadata.text_as_html
            is_html = True
        if elements[i].metadata.page_number:
            page_number = elements[i].metadata.page_number
        extracted_elements[i] = ExtractedElement(
            id=elements[i].id, 
            text=text, 
            page_number=page_number, 
            file_name=name,
            is_html=is_html
        )

    return extracted_elements

