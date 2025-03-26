def __getattr__(name):
    if name == "bundle_api":
        from ._main import bundle_api
        
        return bundle_api
    raise AttributeError(name)
