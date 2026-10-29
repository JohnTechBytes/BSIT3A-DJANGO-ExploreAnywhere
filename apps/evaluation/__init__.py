"""Public usability evaluation module (System Usability Scale).

The module is a URL-only Django module: it owns the survey pages and the form,
while the ``SusResponse`` model stays in ``apps.info`` where it was migrated
(and is registered in the staff dashboard).
"""
