import time 
 
CACHE = {} 
TTL = 60 * 15  # 15 minutes 
 
def get_cached(key): 
    item = CACHE.get(key) 
    if not item: 
        return None 
    if time.time() - item["ts"] > TTL: 
        CACHE.pop(key, None) 
        return None 
    return item["data"] 
 
def set_cached(key, data): 
    CACHE[key] = { 
        "ts": time.time(), 
        "data": data 
    }
