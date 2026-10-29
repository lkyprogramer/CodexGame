from __future__ import annotations
import sys, copy
from pathlib import Path

class StrataCounter:
    """Uses pinned Strata normalization/template/tokenizer; verified against server usage before long tests."""
    def __init__(self,repo,gguf,template):
        sys.path.insert(0,str(Path(repo).resolve()))
        sys.path.insert(0,str(Path(repo).resolve()/'tools'))
        from strata_tokenizer import Tokenizer
        from serve import frontend
        self.frontend=frontend
        self.tokenizer=Tokenizer.from_gguf(gguf)
        self.template=frontend.ChatTemplate(template)
        self.tags=frontend.literal_tags(self.tokenizer.control_tokens)
        self.cache={}

    def __call__(self,body):
        from .core import hash_obj
        key=hash_obj({k:v for k,v in body.items() if k not in ('max_tokens','stream','stream_options')})
        if key in self.cache: return self.cache[key]
        f=self.frontend
        messages,tools,kw=f.openai_to_messages(copy.deepcopy(body))
        if body.get('tool_choice')=='none': tools=None
        messages,tools,changed=f.mark_think_literals(messages,tools,self.tags)
        rendered=self.template.render(messages,tools=tools,**kw)
        if changed:
            rendered,plain=f.unmark_think_literals(rendered,self.tags)
        else: plain=()
        n=len(self.tokenizer.encode(rendered,parse_special=True,plain=plain))
        if len(self.cache)>10000: self.cache.clear()
        self.cache[key]=n
        return n
