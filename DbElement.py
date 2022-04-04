
class DbElement:
    def set_with_dict(self, vars):
        for key, value in vars.items():
            setattr(self, key, value)

    def get_dict(self):
        return {key:value for key, value in self.__dict__.items() if not key.startswith('__') and not callable(key)}

    def set_variable(self, name, value):
        setattr(self, name, value)

    def get_variable(self, name):
        var = getattr(self, name)
        if hasattr(var, '__dict__'):
            var = str(type(var).__name__)
        return var
