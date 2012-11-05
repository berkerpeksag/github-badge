# coding: utf-8

import logging
import os

software = os.environ['SERVER_SOFTWARE'].split('/')[0]
config_name = software.lower().replace(' ', '')

# Currently for a GAE application, possible values for config_name are
# `googleappengine` and `development` as documented here: http://goo.gl/PzmYU
logging.info('Loading configuration for %s', config_name)

try:
    current = __import__(config_name, globals())
except ImportError as err:
    logging.warning('Configuration for %s not found, using defaults',
                    config_name)
    import default as current
