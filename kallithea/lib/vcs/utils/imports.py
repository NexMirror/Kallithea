def import_class(class_path):
    """
    Returns class from the given path.

    For example, in order to get class located at
    ``vcs.backends.hg.MercurialRepository``:

        hgrepo = import_class('vcs.backends.hg.MercurialRepository')
    """
    splitted = class_path.split('.')
    mod_path = '.'.join(splitted[:-1])
    class_name = splitted[-1]
    class_mod = __import__(mod_path, {}, {}, [class_name])
    cls = getattr(class_mod, class_name)
    return cls
