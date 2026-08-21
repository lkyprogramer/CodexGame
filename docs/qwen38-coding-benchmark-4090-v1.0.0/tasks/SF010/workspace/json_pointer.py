_MISSING=object()
def json_pointer_get(document,pointer,default=_MISSING):
    value=document
    for token in pointer.split('/')[1:]:
        value=value[int(token)] if isinstance(value,list) else value[token]
    return value
