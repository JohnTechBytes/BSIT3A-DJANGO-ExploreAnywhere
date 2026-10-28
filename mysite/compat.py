"""Runtime fixes for the Django version that is actually installed.

Why this file exists
--------------------
Django 5.0 and older copy a template context with ``duplicate = copy(super())``
(``django/template/context.py``, ``BaseContext.__copy__``). On CPython 3.13 and
newer that expression returns the ``super`` object itself, so the very next
line — ``duplicate.dicts = ...`` — raises::

    AttributeError: 'super' object has no attribute 'dicts'
    and no __dict__ for setting new attributes

Every inclusion tag copies the context (``InclusionNode.render`` →
``context.new()``), which is why pages such as the Destinations changelist
crashed while other pages looked fine.

Django 5.2 rewrote that method and no longer uses ``copy(super())``, so the real
fix is the Django upgrade pinned in ``requirements.txt``. This module keeps older
installs working too: it probes for the broken behaviour and only replaces the
method when the installed Django actually has the bug.
"""

from copy import copy as _copy

from django.template.context import BaseContext


def _context_copy(self):
    """Equivalent of Django 5.2's fixed ``BaseContext.__copy__``."""
    duplicate = BaseContext()
    duplicate.__class__ = self.__class__
    duplicate.__dict__ = _copy(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


def _context_copy_is_broken():
    """True only when copying a context would raise or lose its dictionaries."""
    try:
        clone = _copy(BaseContext({"probe": True}))
    except Exception:
        return True
    return not isinstance(getattr(clone, "dicts", None), list)


def install():
    """Patch the installed Django only when it needs it. Safe to call twice."""
    if _context_copy_is_broken() and BaseContext.__copy__ is not _context_copy:
        BaseContext.__copy__ = _context_copy
        return True
    return False


CONTEXT_COPY_PATCHED = install()
