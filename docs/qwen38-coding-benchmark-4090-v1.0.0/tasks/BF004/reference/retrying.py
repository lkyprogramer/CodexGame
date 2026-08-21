def retry(action, retries, retry_on, sleep, base_delay=0.1):
    if not callable(action) or not callable(sleep) or not isinstance(retries,int) or isinstance(retries,bool) or retries<0 or base_delay<0:
        raise ValueError('invalid retry arguments')
    if not isinstance(retry_on, tuple): retry_on=(retry_on,)
    if not retry_on or not all(isinstance(t,type) and issubclass(t,Exception) for t in retry_on): raise ValueError('invalid retry_on')
    attempt=0
    while True:
        try:return action()
        except retry_on:
            if attempt>=retries: raise
            sleep(base_delay*(2**attempt));attempt+=1
