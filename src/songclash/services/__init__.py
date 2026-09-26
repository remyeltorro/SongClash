"""Remote data sources (MusicBrainz, Cover Art Archive, iTunes).

Plain blocking Python, no Qt: the UI runs these on background threads via
``songclash.ui.tasks``. To add a source, create a module here that returns
plain dicts in the shape documented by ``songclash.core.models.Song``.
"""
