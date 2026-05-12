import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'DeepPlayer'
copyright = '2026, DeepPlayer'
author = 'DeepPlayer'
release = '1.2'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

html_theme = 'furo'
html_title = 'DeepPlayer 文档'
language = 'zh_CN'
