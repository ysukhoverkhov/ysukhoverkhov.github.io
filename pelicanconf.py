#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Yury Sukhoverkhov'
SITENAME = u'Yury Sukhoverkhov'
SITEURL = 'https://ysukhoverkhov.github.io'

THEME = 'pelican-bootstrap3'

BOOTSTRAP_THEME = 'yeti'
# BOOTSTRAP_THEME = 'simplex'
# BOOTSTRAP_THEME = 'sandstone'
# BOOTSTRAP_THEME = 'lumen'
BOOTSTRAP_FLUID = True

PATH = 'content'

TIMEZONE = 'Europe/Amsterdam'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
# LINKS = (('Pelican', 'http://getpelican.com/'),
#         ('Python.org', 'http://python.org/'),
#         ('Jinja2', 'http://jinja.pocoo.org/'),
#         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('linkedin', 'https://www.linkedin.com/in/ysukhoverkhov/'),
          ('github', 'http://github.com/ysukhoverkhov/'))

DEFAULT_PAGINATION = False

STATIC_PATHS = [
  'static',
]

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

PLUGIN_PATHS = ['../pelican-plugins', ]
PLUGINS = ['i18n_subsites', ]
JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.i18n'],
}

