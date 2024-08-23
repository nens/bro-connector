from flask_caching import Cache

# set cache
TIMEOUT = 60 * 60  # 60 minutes
cache = Cache()
