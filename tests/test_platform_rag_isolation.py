import asyncio
import io
import json
import os
import sys
from unittest.mock import Mock, patch

import numpy as np
import pytest

from agent_platform.rag.embedding import QwenEmbedding
from agent_platform.rag.isolation import ParserFailure, isolated_parse
from agent_platform.rag import parser_worker
from agent_platform.rag.parser import ParseRejected
from test_platform_rag import parsed


@pytest.mark.parametrize('defect', ['job','timeout','exit','size','failed','cancel','gone'])
def test_parser_lifecycle_failure_cleanup(tmp_path,defect):
    process = Mock(pid=123,returncode=None)
    async def communicate(data):
        if defect == 'timeout': raise TimeoutError
        if defect in {'cancel','gone'}: raise asyncio.CancelledError
        process.returncode = 1 if defect == 'exit' else 0
        raw = b'x'*(16*1024*1024+1) if defect == 'size' else json.dumps({'status':'failed','error_code':'parse_failed'}).encode()
        return raw,None
    async def wait(): process.returncode = -9
    process.communicate,process.wait = communicate,wait
    process.kill.side_effect = ProcessLookupError if defect == 'gone' else None
    async def spawn(*args,**kwargs):
        assert all('KEY' not in key for key in kwargs['env'])
        return process
    job = Mock()
    with patch('agent_platform.rag.isolation.asyncio.create_subprocess_exec',spawn),patch(
            'agent_platform.rag.isolation.windows_job',side_effect=RuntimeError if defect == 'job' else None,return_value=job):
        with pytest.raises(asyncio.CancelledError if defect in {'cancel','gone'} else ParserFailure):
            asyncio.run(isolated_parse(tmp_path/'ref.md','text/markdown'))
    if defect != 'job': job.Close.assert_called_once()
    assert process.wait is wait


@pytest.mark.parametrize('defect', ['success','rejected','exception'])
def test_worker_validates_result_and_audit_read_only(tmp_path,defect):
    output,hooks = io.StringIO(),[]
    request = {'path':str(tmp_path/'ref.md'),'media_type':'text/markdown'}
    error = ParseRejected('text_limit') if defect == 'rejected' else ValueError('private detail') if defect == 'exception' else None
    with patch.object(sys,'stdin',Mock(buffer=io.BytesIO(json.dumps(request).encode()))),patch.object(sys,'stdout',output),patch.object(
            sys,'addaudithook',hooks.append),patch('agent_platform.rag.parser.parse_document',side_effect=error,return_value=parsed()):
        parser_worker.main()
    result = json.loads(output.getvalue())
    assert result['status'] == ('succeeded' if defect == 'success' else 'failed')
    assert 'private detail' not in output.getvalue()
    read_only = hooks[-1]
    read_only('open',('path','r',os.O_RDONLY))
    read_only('event',())
    for mode,flags in [('w',0),('a',0),(None,os.O_WRONLY),(None,os.O_CREAT)]:
        with pytest.raises(PermissionError): read_only('open',('path',mode,flags))
    for event in ('socket.connect','subprocess.Popen','os.system'):
        with pytest.raises(PermissionError): hooks[0](event,())


@pytest.mark.parametrize('defect', ['none','shape','nan','zero'])
def test_embedding_pins_bundle_and_checks_vectors(tmp_path,defect):
    weights = tmp_path/'weights'
    weights.write_bytes(b'test-weight-hash-not-a-real-model')
    (tmp_path/'config.json').write_text('{}')
    value = np.zeros((1,1024),dtype=np.float32)
    value[0,0] = 1
    if defect == 'shape': value = value[:,:3]
    if defect == 'nan': value[0,0] = np.nan
    if defect == 'zero': value[0,0] = 0
    model = Mock(encode=Mock(return_value=value))
    factory = Mock(return_value=model)
    with patch('reasoning_agent.strategy_retrieval.ensure_model_weights',return_value=weights),patch.dict(
            sys.modules,{'sentence_transformers':Mock(SentenceTransformer=factory)}):
        encoder = QwenEmbedding(tmp_path)
        if defect == 'none':
            assert len(encoder.encode(['query'],query=True)[0]) == 1024
            encoder.encode(['document'])
            factory.assert_called_once()
            assert model.encode.call_args.kwargs['prompt_name'] is None
        else:
            with pytest.raises(ValueError): encoder.encode(['query'])
