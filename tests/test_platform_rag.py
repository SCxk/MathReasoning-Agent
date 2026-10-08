import asyncio
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import threading
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from rank_bm25 import BM25L
from starlette.datastructures import UploadFile, Headers

from agent_platform.app import create_app
from agent_platform.models import PlatformError, utc_now
from agent_platform.rag.catalog import DocumentCatalog
from agent_platform.rag.index import HybridIndex, tokens, sparse_vector
from agent_platform.rag.isolation import isolated_parse, ParserFailure
from agent_platform.rag.models import Document, MAX_BYTES, ParsedDocument, ParsedChunk
from agent_platform.rag.parser import chunk_pages, evidence_text, ParseRejected, parse_document
from agent_platform.rag.service import DocumentService
from agent_platform.tools.local import LocalTools
from agent_platform.tools.schemas import DocumentValue


class TestEmbedding:
    __test__ = False
    dimensions = 4
    identity = "test-only-no-quality-claims-v1"

    def encode(self, texts, *, query=False):
        return [[1., float('algebra' in text), float('geometry' in text), .25] for text in texts]


def document(session=None, text="algebra formula $x^2$", **values):
    now = utc_now()
    return Document(id=str(uuid4()), session_id=session or str(uuid4()),
        original_name="reference.md", media_type="text/markdown", size_bytes=len(text.encode()),
        content_hash=hashlib.sha256(text.encode()).hexdigest(), storage_key="not-public",
        created_at=now.isoformat(), expires_at=(now + timedelta(days=90)).isoformat(), **values)


def parsed(text="algebra formula $x^2$"):
    return chunk_pages([text])


def arguments(session, **values):
    return {"session_id": session, "query": "algebra formula x^2", "top_k": 5, **values}


@pytest.fixture
def index(tmp_path):
    catalog = DocumentCatalog(tmp_path / "catalog.sqlite")
    client = QdrantClient(":memory:")
    result = HybridIndex(client, catalog, TestEmbedding())
    yield result
    client.close()
    catalog.close()


@pytest.mark.parametrize("formula", ["$$\nx<a>b\n$$", r"\[x^2+y^2\]", "$x<a>b$", r"\(x^2\)", "```python\nx=1\n```"])
def test_formula_is_atomic_and_provenance_preserved(formula):
    result = chunk_pages(["# Method\n" + "a "*900 + formula + "b "*900])
    assert sum(formula in chunk.text for chunk in result.chunks) == 1
    assert all(len(chunk.text) <= 2000 and chunk.heading == "Method" for chunk in result.chunks)
    assert all(chunk.page_start is None for chunk in result.chunks)


@pytest.mark.parametrize("text,code", [
    ("", "no_extractable_text"), ("$$ unclosed", "unclosed_formula_or_fence"),
    ("~~~ unclosed", "unclosed_formula_or_fence"), ("$$" + "x"*2001 + "$$", "formula_too_large"),
    ("$" + "x"*2001 + "$", "formula_too_large"), ("x"*2000001, "text_limit"),
], ids=['empty','unclosed_math','unclosed_fence','large_block','large_inline','large_text'])
def test_parser_rejects_unsafe_or_oversized_blocks(text, code):
    with pytest.raises(ParseRejected, match=code):
        chunk_pages([text])


def test_sanitize_preserves_math_removes_secrets_links_controls():
    output = evidence_text('$x<a>b$ <script>data</script> https://example.org\x00 sk-' + 'a'*24)
    assert '$x<a>b$' in output and '<script>' not in output
    assert 'https://' not in output and 'sk-' not in output and '\x00' not in output


def pdf_bytes(text="Mathematical reference", pages=1):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 12 Tf 20 700 Td ({text}) Tj ET'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("media,name,data", [
    ("text/markdown", "ref.md", b"# Reference\n$$x^2$$"),
    ("application/pdf", "ref.pdf", None),
])
def test_real_parser_subprocess(tmp_path, media, name, data):
    path = tmp_path / name
    path.write_bytes(data or pdf_bytes(pages=2))
    result = asyncio.run(isolated_parse(path, media))
    assert result.chunks
    if media == "application/pdf":
        assert result.page_count == 2 and result.chunks[-1].page_end == 2


def test_invalid_pdf_and_utf8(tmp_path):
    path = tmp_path / 'bad.md'
    path.write_bytes(b'\xff')
    with pytest.raises(ParserFailure, match='invalid_utf8'):
        asyncio.run(isolated_parse(path, 'text/markdown'))
    path.write_bytes(b'%PDF-not-valid')
    with pytest.raises(ParserFailure):
        asyncio.run(isolated_parse(path, 'application/pdf'))


def test_encrypted_page_limit_and_chunk_limit(tmp_path):
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=10,height=10)
    writer.encrypt('private')
    path = tmp_path / 'encrypted.pdf'
    with path.open('wb') as out:
        writer.write(out)
    with pytest.raises(ParseRejected, match='encrypted_pdf'):
        parse_document(path,'application/pdf')
    path.write_bytes(pdf_bytes(pages=501))
    with pytest.raises(ParseRejected, match='page_limit'):
        parse_document(path,'application/pdf')
    with patch('agent_platform.rag.parser.MAX_CHUNKS', 1), pytest.raises(ParseRejected, match='chunk_limit'):
        chunk_pages(['first','second'])


def test_ready_requires_complete_index_and_failure_preserves_snapshot(index):
    first = document()
    index.catalog.reserve(first)
    assert index.search(arguments(first.session_id)) == {"passages": []}
    index.ingest(first, parsed())
    before = index.catalog.snapshot(first.session_id)
    second = document(first.session_id, text='geometry')
    index.catalog.reserve(second)
    with patch.object(index.client, 'upsert', side_effect=RuntimeError('private failure')):
        with pytest.raises(RuntimeError):
            index.ingest(second, parsed('geometry'))
    index.catalog.fail(second, 'indexing_failed')
    assert index.catalog.snapshot(first.session_id) == before
    found = index.search(arguments(first.session_id))['passages']
    assert {item['document_id'] for item in found} == {first.id}
    DocumentValue.model_validate({'passages': found})
    index.reconcile()
    assert len(index.client.get_collections().collections) == 1
    index.ingest(first, parsed())
    assert index.catalog.snapshot(first.session_id) == before


@pytest.mark.parametrize('pair', range(100))
def test_100_paired_session_isolation(index, pair):
    first, other = document(text=f'algebra {pair}'), document(text=f'geometry {pair}')
    for doc in (first,other):
        index.catalog.reserve(doc)
        index.ingest(doc,parsed(doc.content_hash))
    found = index.search(arguments(first.session_id))['passages']
    assert found and {item['document_id'] for item in found} == {first.id}
    assert not index.search(arguments(first.session_id, document_ids=[other.id]))['passages']
    with pytest.raises(PlatformError):
        index.catalog.get(other.session_id,first.id)


@pytest.mark.parametrize('field', ['domain','problem_type','source','document_ids'])
def test_strict_filters(index, field):
    doc = document(domain='algebra',problem_type='proof',source='textbook')
    index.catalog.reserve(doc)
    index.ingest(doc,parsed())
    yes = [doc.id] if field == 'document_ids' else getattr(doc,field)
    no = [str(uuid4())] if field == 'document_ids' else 'other'
    assert index.search(arguments(doc.session_id,**{field:yes}))['passages']
    assert not index.search(arguments(doc.session_id,**{field:no}))['passages']


def test_bm25l_sparse_inner_product_matches_pinned_library(index):
    doc = document()
    index.catalog.reserve(doc)
    parts = ParsedDocument(page_count=None,chunks=[ParsedChunk(text=text) for text in ['algebra algebra x^2','geometry x','algebra x']])
    index.ingest(doc,parts)
    name = index.catalog.snapshot(doc.session_id)[0]
    points,_ = index.client.scroll(name,limit=100,with_vectors=True)
    points.sort(key=lambda item:str(item.id))
    query = tokens('algebra algebra x')
    scores = BM25L([tokens(item.payload['text']) for item in points]).get_scores(query)
    vector = sparse_vector(__import__('collections').Counter(query))
    for point,want in zip(points,scores):
        stored = dict(zip(point.vector['sparse'].indices,point.vector['sparse'].values))
        actual = sum(stored.get(i,0)*v for i,v in zip(vector.indices,vector.values))
        assert actual == pytest.approx(want,rel=1e-6)


def test_expired_docs_cannot_be_retrieved(index):
    doc = document()
    index.catalog.reserve(doc)
    index.ingest(doc,parsed())
    doc.expires_at = (utc_now()-timedelta(seconds=1)).isoformat()
    index.catalog.expire(doc)
    index.purge(doc.id)
    assert not index.search(arguments(doc.session_id))['passages']


def test_upload_api_and_restart_resume(tmp_path):
    store = __import__('agent_platform.storage',fromlist=['InMemoryTaskStore']).InMemoryTaskStore()
    service = DocumentService(tmp_path,TestEmbedding())
    with TestClient(create_app(store=store,documents=service,rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        url = f'/v1/sessions/{session}/documents'
        result = client.post(url,files={'file':('reference.md',b'# Algebra\n$$x^2$$','text/markdown')},data={'domain':'algebra'})
        assert result.status_code == 202,result.text
        item = result.json()
        assert 'storage_key' not in item and 'C:' not in result.text
        import time
        for _ in range(100):
            status = client.get(item['status_url']).json()
            if status['status'] != 'indexing':
                break
            time.sleep(.05)
        assert status['status'] == 'ready', status
        assert client.post(url,files={'file':('reference.md',b'# Algebra\n$$x^2$$','text/markdown')}).status_code == 409
        other = client.post('/v1/sessions').json()['id']
        assert client.get(item['status_url'].replace(session,other)).status_code == 404
    recovered = DocumentService(tmp_path,TestEmbedding())
    async def check():
        await recovered.start()
        try:
            result = await recovered.search(arguments(session))
            assert result['passages'][0]['document_id'] == item['id']
        finally:
            await recovered.stop()
    asyncio.run(check())


@pytest.mark.parametrize('name,mime,body,code', [
    ('bad.txt','text/plain',b'x',415), ('bad.md','application/pdf',b'x',400),
    ('bad.pdf','application/pdf',b'not PDF',400), ('bad.md','text/markdown',b'%PDF-x',400),
    ('bad.md','text/markdown',b'PK\x03\x04',400), ('empty.md','text/markdown',b'',400),
    ('large.md','text/markdown',b'x'*(MAX_BYTES+1),413),
], ids=['extension','mime','pdf_signature','md_signature','archive','empty','size'])
def test_upload_rejections(tmp_path,name,mime,body,code):
    documents = DocumentService(tmp_path,TestEmbedding())
    with TestClient(create_app(documents=documents,rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        response = client.post(f'/v1/sessions/{session}/documents',files={'file':(name,body,mime)})
        assert response.status_code == code,response.text
        assert not documents.catalog.documents()
        assert not list((tmp_path/'quarantine').glob('*'))


def test_single_process_ownership_and_pending_recovery(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    with pytest.raises(ValueError,match='already_owned'):
        DocumentService(tmp_path,TestEmbedding())
    doc = document()
    doc.storage_key = f'blobs/{doc.session_id}/{doc.content_hash}'
    blob = tmp_path/doc.storage_key
    blob.parent.mkdir(parents=True)
    blob.write_text('algebra formula $x^2$',encoding='utf8')
    service.catalog.reserve(doc)
    async def run():
        await service.start()
        for _ in range(100):
            if service.catalog.get(doc.session_id,doc.id).status == 'ready':
                break
            await asyncio.sleep(.05)
        assert service.catalog.get(doc.session_id,doc.id).status == 'ready'
        await service.stop()
    asyncio.run(run())


def test_shutdown_waits_for_real_index_thread(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    started, release = threading.Event(),threading.Event()
    original = service.index.ingest
    def blocked(*args):
        started.set()
        release.wait(5)
        return original(*args)
    async def run():
        await service.start()
        file = UploadFile(io.BytesIO(b'algebra'),filename='ref.md',headers=Headers({'content-type':'text/markdown'}))
        await service.upload(str(uuid4()),file)
        assert await asyncio.to_thread(started.wait,3)
        stopping = asyncio.create_task(service.stop())
        await asyncio.sleep(.1)
        assert not stopping.done()
        release.set()
        await stopping
    with patch.object(service.index,'ingest',blocked):
        asyncio.run(run())


def test_document_tool_returns_typed_citations(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    doc = document()
    service.catalog.reserve(doc)
    service.index.ingest(doc,parsed())
    async def run():
        await service.start()
        result = await LocalTools(documents=service).invoke('document_search',arguments(doc.session_id))
        assert result['status'] == 'succeeded'
        DocumentValue.model_validate(result['value'])
        assert result['citations'] == [item['chunk_id'] for item in result['value']['passages']]
        await service.stop()
    asyncio.run(run())


def test_upload_stream_limit_without_content_length(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    with TestClient(create_app(documents=service,rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        prefix = b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="ref.md"\r\nContent-Type: text/markdown\r\n\r\n'
        def content():
            yield prefix
            for _ in range(22):
                yield b'x'*(1024*1024)
            yield b'\r\n--boundary--\r\n'
        response = client.post(f'/v1/sessions/{session}/documents',content=content(),
                              headers={'Content-Type':'multipart/form-data; boundary=boundary'})
        assert response.status_code == 413,response.text
        assert not service.catalog.documents()


@pytest.mark.parametrize('length', ['not-a-number','-1',str(MAX_BYTES+65537)])
def test_upload_declared_body_limit(tmp_path,length):
    service = DocumentService(tmp_path,TestEmbedding())
    with TestClient(create_app(documents=service,rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        response = client.post(f'/v1/sessions/{session}/documents',content=b'x',headers={'Content-Length':length})
        assert response.status_code == (400 if length == 'not-a-number' else 413)


def test_parser_direct_paths_heading_fence_and_math(tmp_path):
    path = tmp_path/'reference.md'
    path.write_text('# A\n\ntext\n\n# B\n~~~\ncode\n~~~\n\\[x>0\\]',encoding='utf8')
    result = parse_document(path,'text/markdown')
    assert {part.heading for part in result.chunks} == {'A','B'}
    path.write_bytes(b'\xff')
    with pytest.raises(ParseRejected,match='invalid_utf8'):
        parse_document(path,'text/markdown')
    path.write_bytes(pdf_bytes(pages=2))
    assert parse_document(path,'application/pdf').chunks[-1].page_start == 2
    with patch('agent_platform.rag.parser.MAX_TEXT',1), pytest.raises(ParseRejected,match='text_limit'):
        parse_document(path,'application/pdf')


@pytest.mark.parametrize('defect', ['version','invalid_vectors','count','active_shadow','foreign_hit','result_size','empty_query'])
def test_index_failure_guards(index,defect):
    doc = document()
    index.catalog.reserve(doc)
    if defect == 'invalid_vectors':
        with patch.object(index.embedder,'encode',return_value=[[float('nan')]*4]),pytest.raises(ValueError,match='invalid_embeddings'):
            index.ingest(doc,parsed())
        return
    if defect == 'count':
        from unittest.mock import Mock
        with patch.object(index.client,'count',return_value=Mock(count=0)),pytest.raises(ValueError,match='index_count_mismatch'):
            index.ingest(doc,parsed())
        return
    if defect == 'active_shadow':
        with patch.object(index.client,'collection_exists',return_value=True),patch.object(index.catalog,'collections') as collections:
            # Compute the exact attempted collection from the create/delete guard.
            records = []
            def active(name):
                collections.return_value = {name}
                return True
            with patch.object(index.client,'collection_exists',side_effect=active),pytest.raises(ValueError,match='active_snapshot_conflict'):
                index.ingest(doc,parsed())
        return
    index.ingest(doc,parsed())
    if defect == 'version':
        index.version = 'incompatible'
        with pytest.raises(ValueError,match='reindex_required'):
            index.search(arguments(doc.session_id))
        second = document(doc.session_id,text='changed')
        index.catalog.reserve(second)
        with pytest.raises(ValueError,match='reindex_required'):
            index.ingest(second,parsed())
    if defect == 'foreign_hit':
        from unittest.mock import Mock
        hit = Mock(payload={'session_id':'other'},id=doc.id,score=1.)
        with patch.object(index.client,'query_points',return_value=Mock(points=[hit])),pytest.raises(ValueError,match='retrieval_scope_violation'):
            index.search(arguments(doc.session_id))
    if defect == 'result_size':
        # Unicode bytes, not Python character count, determine the transport limit.
        with patch('agent_platform.rag.index.json.dumps',return_value='x'*60001):
            assert not index.search(arguments(doc.session_id))['passages']
    if defect == 'empty_query':
        assert index.search(arguments(doc.session_id,query=''))['passages']
        assert tokens('中') == ['中']


def test_shadow_retry_and_rank_formula(index):
    doc = document(domain='algebra')
    index.catalog.reserve(doc)
    with patch.object(index.client,'upsert',side_effect=RuntimeError):
        with pytest.raises(RuntimeError): index.ingest(doc,parsed('x^2'))
    index.ingest(doc,parsed('x^2'))
    hit = index.search(arguments(doc.session_id,query='x^2',domain='algebra'))['passages'][0]
    assert hit['scores']['rerank'] == pytest.approx(1.)


def test_catalog_capacity_stale_and_failed_guard(index):
    for _ in range(16):
        index.catalog.reserve(document())
    with pytest.raises(PlatformError,match='ingestion_capacity_exceeded'):
        index.catalog.reserve(document())
    first = index.catalog.documents()[0]
    index.catalog.fail(first,'parse_failed')
    with pytest.raises(PlatformError,match='stale_ingestion'):
        index.catalog.activate(first,[],[], 'name','version','hash',None)


def test_service_failure_reconciliation_and_storage_guards(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    expired = document()
    expired.expires_at = (utc_now()-timedelta(seconds=1)).isoformat()
    service.catalog.reserve(expired)
    orphan = tmp_path/'quarantine'/'old-upload'
    orphan.parent.mkdir(exist_ok=True)
    orphan.write_bytes(b'old')
    import os,time
    os.utime(orphan,(time.time()-7200,)*2)
    service.maintenance()
    assert not orphan.exists() and service.catalog.get(expired.session_id,expired.id).status == 'expired'
    async def run():
        file = lambda:UploadFile(io.BytesIO(b'algebra'),filename='ref.md',headers=Headers({'content-type':'text/markdown'}))
        with pytest.raises(PlatformError,match='document_service_unavailable'):
            await service.upload(str(uuid4()),file())
        await service.start()
        with patch('agent_platform.rag.service.shutil.disk_usage',return_value=__import__('types').SimpleNamespace(free=0)),pytest.raises(PlatformError,match='storage_capacity_exceeded'):
            await service.upload(str(uuid4()),file())
        with pytest.raises(PlatformError,match='invalid_document_metadata'):
            await service.upload(str(uuid4()),file(),domain='x'*101)
        missing = document()
        service.catalog.reserve(missing)
        service.signal.set()
        for _ in range(100):
            if service.catalog.get(missing.session_id,missing.id).status == 'failed': break
            await asyncio.sleep(.02)
        assert service.catalog.get(missing.session_id,missing.id).error_code == 'blob_integrity_failed'
        await service.stop()
        with pytest.raises(ValueError,match='unavailable'):
            await service.search(arguments(str(uuid4())))
    asyncio.run(run())


def test_index_exception_marks_failed_with_no_private_detail(tmp_path):
    async def parser(path,media): return parsed()
    service = DocumentService(tmp_path,TestEmbedding(),parser=parser)
    async def run():
        await service.start()
        file = UploadFile(io.BytesIO(b'algebra'),filename='ref.md',headers=Headers({'content-type':'text/markdown'}))
        item = await service.upload(str(uuid4()),file)
        for _ in range(100):
            status = service.get(item['session_id'],item['id'])
            if status['status'] == 'failed': break
            await asyncio.sleep(.02)
        assert status['error_code'] == 'indexing_failed' and 'secret' not in json.dumps(status)
        await service.stop()
    with patch.object(service.index,'ingest',side_effect=RuntimeError('private secret')):
        asyncio.run(run())


def test_upload_unavailable_malformed_form_and_failed_readiness(tmp_path):
    with TestClient(create_app(rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        root = f'/v1/sessions/{session}/documents'
        assert client.post(root).status_code == 503
        assert client.get(f'{root}/{uuid4()}').status_code == 503
    service = DocumentService(tmp_path,TestEmbedding())
    with TestClient(create_app(documents=service,rate_limits=False)) as client:
        session = client.post('/v1/sessions').json()['id']
        url = f'/v1/sessions/{session}/documents'
        assert client.post(url,data={'source':'text'}).status_code == 400
        assert client.post(url,files={'file':('ref.md',b'x','text/markdown')},data={'extra':'x'}).status_code == 400
        assert client.post(url,files=[('file',('ref.md',b'x','text/markdown')),('source',('other.md',b'x','text/markdown'))]).status_code == 400
        service.accepting = False
        assert client.get('/health/ready').status_code == 503


def test_service_search_backpressure_and_stop_before_start(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    async def run():
        for _ in range(8): service.permits.acquire()
        with pytest.raises(ValueError,match='unavailable'):
            await service.search(arguments(str(uuid4())))
        service.accepting = True
        work = asyncio.create_task(service.search(arguments(str(uuid4()))))
        await asyncio.sleep(.03)
        assert not work.done()
        for _ in range(8): service.permits.release()
        assert await work == {'passages':[]}
        await service.stop()
    asyncio.run(run())


def test_constructor_failure_releases_catalog_and_owner(tmp_path):
    with patch('agent_platform.rag.service.DocumentCatalog',side_effect=RuntimeError('catalog unavailable')):
        with pytest.raises(RuntimeError): DocumentService(tmp_path,TestEmbedding())
    with patch('qdrant_client.QdrantClient',side_effect=RuntimeError('index unavailable')):
        with pytest.raises(RuntimeError): DocumentService(tmp_path,TestEmbedding())
    service = DocumentService(tmp_path,TestEmbedding())
    asyncio.run(service.stop())


def test_worker_expiry_and_maintenance_failure_are_closed(tmp_path):
    service = DocumentService(tmp_path,TestEmbedding())
    expired = document()
    expired.expires_at = (utc_now()-timedelta(seconds=1)).isoformat()
    service.catalog.reserve(expired)
    async def run():
        service.accepting = True
        async def timeout(awaitable,*args):
            awaitable.close()
            raise TimeoutError
        with patch('agent_platform.rag.service.asyncio.wait_for',timeout),patch.object(
                service,'maintenance',side_effect=RuntimeError('dependency unavailable')):
            await service._work()
        assert not service.accepting and service.stopping
        assert service.catalog.get(expired.session_id,expired.id).status == 'expired'
        await service.stop()
    asyncio.run(run())
