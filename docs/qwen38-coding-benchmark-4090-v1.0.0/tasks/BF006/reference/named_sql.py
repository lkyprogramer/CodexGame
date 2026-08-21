def compile_named(sql, params):
    if not isinstance(sql,str):raise ValueError('sql must be string')
    out=[];values=[];i=0;state='code'
    while i<len(sql):
        c=sql[i];n=sql[i+1] if i+1<len(sql) else ''
        if state=='single':
            out.append(c)
            if c=="'":
                if n=="'":out.append(n);i+=2;continue
                state='code'
            i+=1;continue
        if state=='double':
            out.append(c)
            if c=='"':
                if n=='"':out.append(n);i+=2;continue
                state='code'
            i+=1;continue
        if state=='line':
            out.append(c);i+=1
            if c=='\n':state='code'
            continue
        if state=='block':
            out.append(c)
            if c=='*' and n=='/':out.append('/');i+=2;state='code';continue
            i+=1;continue
        if c=="'":state='single';out.append(c);i+=1;continue
        if c=='"':state='double';out.append(c);i+=1;continue
        if c=='-' and n=='-':state='line';out.extend([c,n]);i+=2;continue
        if c=='/' and n=='*':state='block';out.extend([c,n]);i+=2;continue
        if c==':' and n==':':out.extend([c,n]);i+=2;continue
        if c==':' and (n.isalpha() or n=='_'):
            j=i+2
            while j<len(sql) and (sql[j].isalnum() or sql[j]=='_'):j+=1
            name=sql[i+1:j]
            if name not in params:raise KeyError(name)
            out.append('?');values.append(params[name]);i=j;continue
        out.append(c);i+=1
    if state in ('single','double','block'):raise ValueError('unterminated SQL construct')
    return ''.join(out),values
