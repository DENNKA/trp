import inspect

def base_decorator_for_init(cls, orig_func):
    def decorator(*args, **kwargs):
         cls.init(args[0])
         result = orig_func(*args, **kwargs)
         return result
    return decorator

def lazy_init(decorator, exclude=["init"]):

    class Decorator(object):
        def __init__(self, cls):
            self.cls = cls

        def __call__(self, *args, **kwargs):
            for name, method in inspect.getmembers(self.cls):
                if name in exclude or name.startswith('_') or (not inspect.ismethod(method) and not inspect.isfunction(method)) or inspect.isbuiltin(method):
                    continue
                setattr(self.cls, name, decorator(self.cls, method))
            return self.cls(*args, **kwargs)

    return Decorator
