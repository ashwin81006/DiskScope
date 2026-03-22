class FileNode:
    def __init__(self, name, size, children=None):
        self.name = name
        self.size = size
        self.children = children or []