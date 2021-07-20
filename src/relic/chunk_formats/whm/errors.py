
class UnimplementedMslcBlockFormat(NotImplementedError):
    def __init__(self, format_code: int, *args):
        super().__init__(format_code, *args) # we include format code in super so that NotImplemented can see it too
        self.format = format_code

