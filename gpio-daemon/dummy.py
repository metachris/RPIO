class DummyFunction(object):
    def __init__(self, name):
        self.name = name

    def call(self, *args, **kwargs):
        # Instead of doing anything, the dummy only prints which function was called
        print "%s(%s, %s) called on Dummy object" % (self.name,
                ", ".join([repr(x) for x in args]), kwargs)

    def __repr__(self):
        return self.name


class Dummy(object):
    def __init__(self):
        pass

    def __getattr__(self, name):
        return DummyFunction(name).call
