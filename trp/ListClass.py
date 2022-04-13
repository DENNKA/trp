
class ListClass():
    def get_all(self):
        return self.classes.keys()

    def get_all_classes(self, raise_on_error=False):
        for class1 in self.classes.values():
            try:
                class1.init(self.cfg)
            except Exception:
                if raise_on_error:
                    raise
        return list(self.classes.values())

    def get_class(self, name, raise_on_error=False):
        if not name:
            return None
        class1 = self.classes[name]
        try:
            class1.init(self.cfg)
        except Exception:
            if raise_on_error:
                raise
        return class1
