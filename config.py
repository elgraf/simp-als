import logging
import sys
from os import environ

HTTP_PORT = int(environ.get('HTTP_PORT', 8000))
BIND_ADDRESS = environ.get('BIND_ADDRESS', '0.0.0.0')

MONGO_SERVER = environ.get('MONGO_SERVER', 'db:27017')
REDIS_SERVER = environ.get('REDIS_SERVER', 'redis:6379')
REDIS_NAMESPACE = environ.get('REDIS_NAMESPACE', 'simpalspipe:')

DATABASE_NAME = environ.get('DATABASE_NAME', 'feeds')
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

FETCH_INTERVAL = int(environ.get('FETCH_INTERVAL', 50))
CHECK_INTERVAL = int(environ.get('CHECK_INTERVAL', 10))
MAX_CONCURRENT_REQUESTS = int(environ.get('MAX_CONCURRENT_REQUESTS', 100))

ALL_ADVERTS_URL = environ.get('ALL_ADVERTS_ULR', 'https://partners-api.999.md/adverts?page_size=100&page={}'
                                                 '&states=public,hidden,blocked,blocked_commercial,expired')
DETAILED_ADVERT = environ.get('DETAILED_ADVERT', 'https://partners-api.999.md/adverts/{}')
EXCHANGE_URL = environ.get('EXCHANGE_URL', 'https://www.bnm.md/en/export-official-exchange-rates?date={}')
API_KEY = environ.get('API_KEY', 'apuUo-UFwisHbYFUSs24ZvEgVOkc')

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()

log.info("Configuration loaded.")
