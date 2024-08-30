from plum.harnesslib.languages import Language


class PromptCreation:
    """
    Ties all prompt pieces together into one full string
    that is the prompt to pass to codex
    """

    def __init__(self, prompt_pieces):
        self.prompt_pieces = prompt_pieces
        self.prompt = ""
        self.prompt = self.combine()

    def combine(self):
        """
        Iterates through the prompt pieces passed to Prompt Creation
        Appends them together into one string prompt passed to Codex
        """
        for piece in self.prompt_pieces:
            self.prompt += piece.input_string

        return self.prompt

    def __str__(self):
        return self.prompt


class PromptPiece:
    """
    Parent class of all sub-pieces of a prompt to feed to codex
    """

    def __init__(self, input_string):
        self.input_string = input_string


class FocalMethod(PromptPiece):
    def __init__(self, input_string):
        super().__init__(input_string)
        self.input_string += "\n"


class Comment(PromptPiece):
    def __init__(self, input_string, language):
        super().__init__(input_string)
        if language == Language.Javascript:
            self.input_string = "// " + self.input_string + "\n"
        if language == Language.Python:
            self.input_string = "#" + self.input_string + "\n"
        if language == Language.Typescript:
            self.input_string = "// " + self.input_string + "\n"


class Imports(PromptPiece):
    def __init__(self, input_string):
        super().__init__(input_string)
        self.input_string += "\n"


class Docstring(PromptPiece):
    def __init__(self, input_string, language):
        super().__init__(input_string)
        if language == Language.Javascript:
            self.input_string = "/*\n" + input_string + "\n*/\n"
        if language == Language.Python:
            self.input_string = '"""\n' + self.input_string + '\n"""\n'
        if language == Language.Typescript:
            self.input_string = "/*\n" + input_string + "\n*/\n"


class GenerationPrefix(PromptPiece):
    def __init__(self, input_string):
        super().__init__(input_string)
