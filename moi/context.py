from IPython.parallel import Client


class Context(object):
    def __init__(self, profile):
        self.client = Client(profile=profile)
        self.bv = self.client.load_balanced_view()
