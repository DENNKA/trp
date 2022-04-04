
class ListClass():
    def get_all(self):
        return self.classes.keys()

    def get_class(self, name):
        if not name:
            return None
        class1 = self.classes[name]
        try:
            class1.init(self.cfg)
        except Exception:
            pass
        return class1
