import pymysql
pymysql.install_as_MySQLdb()

# Works around a Django < 5.1 context-copy bug on Python 3.13+ (see the module).
from . import compat  # noqa: E402,F401  (imported for its side effect)
