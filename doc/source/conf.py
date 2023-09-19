# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pkg_resources import get_distribution

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Quibble'
author = ('Antoine Musso, Kunal Mehta, Timo Tijhof, Tyler Cipriani, '
          'Wikimedia Foundation Inc.')
copyright = '2014 - 2018, ' + author

# The full version, including alpha/beta/rc tags
release = get_distribution('quibble').version
# The short X.Y version
version = release


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinxarg.ext',
    'sphinx.ext.autodoc',
    # 'sphinx.ext.autosectionlabel',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['doc/build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = []

# -- Extension configuration -------------------------------------------------

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
