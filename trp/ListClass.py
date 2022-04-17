
class ListClass():
    def get_all(self):
        return self.classes.keys()

    def get_all_classes(self):
        return list(self.classes.values())

    def get_class(self, name):
        if not name:
            return name
        class1 = self.classes[name]
        return class1
