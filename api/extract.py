from fastapi import APIRouter, Request, Response
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.strategies import PartitionStrategy
from pydantic import BaseModel
import logging
import json
from typing import List, Optional, Generator
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

def is_next_element_same_page(element: ExtractedElement, next_element: ExtractedElement)->bool:
    return (element.page_number is None or element.page_number == next_element.page_number) and (element.file_name is None or element.file_name == next_element.file_name)

def generate_chunks(extracted_elements: List[ExtractedElement])->Generator[ExtractedElement, None, None]:
    next_chunk = ExtractedElement(id="", is_html=False, text="", page_number=None, file_name="")
    combined_chunk_ids = []
    for element in extracted_elements:
        if element.is_html:
            yield element
        elif element.page_number is None or element.text == '':
            continue
        elif is_next_element_same_page(next_chunk, element):
            next_chunk.page_number = element.page_number
            next_chunk.file_name = element.file_name
            next_chunk.text += element.text+'\n'
            combined_chunk_ids.append(element.id)
        else:
            next_chunk.id = str(hash(''.join(combined_chunk_ids)))
            yield next_chunk
            next_chunk = ExtractedElement(
                id="", 
                is_html=False, 
                text=element.text+'\n', 
                page_number=element.page_number, 
                file_name=element.file_name
            )
            combined_chunk_ids = [element.id]
    next_chunk.id = str(hash(''.join(combined_chunk_ids)))
    yield next_chunk

def save_chunks(chunks: List[ExtractedElement], file_path: str):
    with open(f'{file_path}_chunks.json', 'w') as f:
        json.dump(chunks,f)

@router.post("/extract")
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

@router.post("/extract-chunks")
async def extract_chunks(request: Request, name:str)->List[ExtractedElement]:
    extracted_elements = await extract(request, name)
    chunked_elements = [chunk for chunk in generate_chunks(extracted_elements)]
    save_chunks(chunked_elements, name)
    return Response(status_code=200)