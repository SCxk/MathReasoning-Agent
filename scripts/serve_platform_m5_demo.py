"""Real reference indexing, fake reasoning; no answer-quality claims."""

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import uvicorn
from agent_platform.app import create_app
from agent_platform.rag.embedding import QwenEmbedding
from agent_platform.rag.service import DocumentService
from agent_platform.runtime import RuntimeResult, STAGES
from agent_platform.tools.local import LocalTools
from agent_platform.tools.registry import ToolRegistry, stable_call_id
from agent_platform.tools.schemas import ToolInvocation


class RAGProtocolDemo:
    name = 'fake_reasoning_real_rag_demo'

    def __init__(self,documents):
        self.tools = ToolRegistry(LocalTools(documents=documents))

    async def run(self,context):
        for stage in STAGES:
            context.progress(stage)
            await asyncio.sleep(.25)
            if stage == 'retrieve':
                args = {'session_id':context.session_id,'query':context.problem[:4000],'top_k':5}
                context.record(stage,'retrieval.started',{'source':'documents'})
                result = await self.tools.invoke(ToolInvocation(call_id=stable_call_id(context,stage,'demo','document_search',args),
                    task_id=context.task_id,stage_id=stage,tool_name='document_search',arguments=args),context)
                passages = result.value['passages'] if result.value else []
                context.record(stage,'retrieval.completed',{'source':'documents','hit_count':len(passages),
                    'references':[{key:part[key] for key in ('chunk_id','document_id','source_metadata','page_start','page_end','scores')} for part in passages],
                    'status':'retrieved_not_used_by_fake_runtime'})
            context.progress(stage,completed=True,checkpoint={'completed_stage':STAGES.index(stage)})
        return RuntimeResult('Fake Runtime completed. Real document retrieval only; no mathematical answer was generated.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8003)
    parser.add_argument('--rag-dir',type=Path,default=Path('sample_outputs/platform_m5/demo'))
    parser.add_argument('--embedding-model-dir',type=Path,default=Path('strategyrag/Qwen3-Embedding-0.6B'))
    args = parser.parse_args()
    import torch
    torch.set_num_threads(4)
    documents = DocumentService(args.rag_dir,QwenEmbedding(args.embedding_model_dir))
    uvicorn.run(create_app(documents=documents,runtime=RAGProtocolDemo(documents)),host='127.0.0.1',port=args.port,access_log=False)
