"""Real offline encoder/Qdrant/parser smoke, not labelled retrieval evaluation."""

import argparse
import asyncio
import io
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from starlette.datastructures import Headers, UploadFile

from agent_platform.rag.embedding import QwenEmbedding
from agent_platform.rag.service import DocumentService


def file(text):
    return UploadFile(io.BytesIO(text.encode()),filename='reference.md',headers=Headers({'content-type':'text/markdown'}))


def pdf_file():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=612,height=792)
    font = writer._add_object(DictionaryObject({NameObject('/Type'):NameObject('/Font'),
        NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 700 Td (Geometry: distance squared d^2 = dx^2 + dy^2.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return UploadFile(output,filename='geometry.pdf',headers=Headers({'content-type':'application/pdf'}))


async def wait_ready(service,session,identifier):
    for _ in range(1200):
        status = service.get(session,identifier)
        if status['status'] != 'indexing':
            if status['status'] != 'ready': raise RuntimeError(status['error_code'])
            return status
        await asyncio.sleep(.1)
    raise TimeoutError('smoke_ingestion_timeout')


async def main(args):
    import torch
    torch.set_num_threads(4)
    service = DocumentService(args.rag_dir,QwenEmbedding(args.embedding_model_dir))
    if args.crash_child:
        def crash(*_): os._exit(73)
        service.catalog.activate = crash
        await service.start()
        await service.upload(args.session,pdf_file(),domain='geometry')
        await asyncio.sleep(120)
        raise RuntimeError('crash_boundary_not_reached')
    session = str(uuid4())
    await service.start()
    item = await service.upload(session,file('# Algebra\n$$ (a+b)^2 = a^2+2ab+b^2 $$'),domain='algebra')
    await wait_ready(service,session,item['id'])
    first = await service.search({'session_id':session,'query':'polynomial identity (a+b)^2', 'top_k':5,'domain':'algebra'})
    assert first['passages'] and first['passages'][0]['document_id'] == item['id']
    identity = service.identity
    await service.stop()
    child = subprocess.Popen([sys.executable,__file__,'--crash-child','--rag-dir',str(args.rag_dir),
        '--embedding-model-dir',str(args.embedding_model_dir),'--session',session],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=0x08000000 if os.name == 'nt' else 0)
    try:
        assert await asyncio.to_thread(child.wait,120) == 73
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    started = time.monotonic()
    recovered = DocumentService(args.rag_dir,QwenEmbedding(args.embedding_model_dir))
    pending = recovered.catalog.documents(session,'indexing')
    assert len(pending) == 1
    # Old snapshot remains readable immediately, before the interrupted upload resumes.
    assert recovered.catalog.get(session,item['id']).status == 'ready'
    await recovered.start()
    try:
        await wait_ready(recovered,session,pending[0].id)
        result = await recovered.search({'session_id':session,'query':'distance squared geometry', 'top_k':5,'domain':'geometry'})
        assert result['passages'] and result['passages'][0]['document_id'] == pending[0].id
        assert result['passages'][0]['page_start'] == result['passages'][0]['page_end'] == 1
        assert not (await recovered.search({'session_id':str(uuid4()),'query':'geometry','top_k':5}))['passages']
        print(json.dumps({'check':'real_qwen_qdrant_parser_crash_recovery','status':'passed',
            'dimensions':1024,'index_version':identity,'recovery_seconds':round(time.monotonic()-started,3),
            'quality_metrics':'not_measured_no_human_labels','model_calls':0}))
    finally:
        await recovered.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rag-dir',type=Path)
    parser.add_argument('--embedding-model-dir',type=Path,default=Path('strategyrag/Qwen3-Embedding-0.6B'))
    parser.add_argument('--crash-child',action='store_true')
    parser.add_argument('--session')
    args = parser.parse_args()
    if args.rag_dir is None:
        output = Path('sample_outputs/platform_m5')
        output.mkdir(parents=True,exist_ok=True)
        args.rag_dir = Path(tempfile.mkdtemp(prefix='smoke-',dir=output)).resolve()
    asyncio.run(main(args))
