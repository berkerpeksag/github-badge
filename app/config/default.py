# coding: utf-8


DEBUG = False

PARAMETERS = ('a', 's',)

GITHUB_API_AUTH = {
    'type': 'app',
    'client_id': 'github_app_client_id',
    'client_secret': 'github_app_client_secret'
}

MEMCACHE_EXPIRATION = 60 * 60 * 24  # 1 day in seconds
RECENT_DAYS = 7

MAX_COMMITS_PER_BRANCH = 200
