_MISSING = object()

def _decode(token):
    out=[]; i=0
    while i < len(token):
        if token[i] != '~': out.append(token[i]); i += 1; continue
        if i+1 >= len(token) or token[i+1] not in '01': raise ValueError('invalid escape')
        out.append('~' if token[i+1]=='0' else '/'); i += 2
    return ''.join(out)

def json_pointer_get(document, pointer, default=_MISSING):
    if not isinstance(pointer,str): raise ValueError('pointer must be string')
    if pointer == '': return document
    if not pointer.startswith('/'): raise ValueError('pointer must start with slash')
    value=document
    try:
        for raw in pointer[1:].split('/'):
            token=_decode(raw)
            if isinstance(value,dict):
                value=value[token]
            elif isinstance(value,list):
                if token == '-' or not (token == '0' or (token.isdigit() and not token.startswith('0'))): raise ValueError('invalid array index')
                index=int(token)
                if index >= len(value): raise KeyError(token)
                value=value[index]
            else:
                raise KeyError(token)
        return value
    except (KeyError, IndexError):
        if default is not _MISSING: return default
        raise KeyError(pointer)
