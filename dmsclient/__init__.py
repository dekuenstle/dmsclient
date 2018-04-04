try:
    from dmsclient.core import *
except ImportError as e:
    pass

__version__ = '1.5.0'
__author__ = 'David-Elias Künstle'
__author_email__ = 'dmsclient' + chr(64) + 'kuenstle.me'  # hide of dumb email crawler
__description__ = 'Library and command line interface to interact with Drink Management System of Fachschaft TF Uni Freiburg.'
