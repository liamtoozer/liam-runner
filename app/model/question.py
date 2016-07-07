from app.model.display import Display


class Question(object):
    def __init__(self):
        self.id = None
        self.title = None
        self.description = ""
        self.answers = []
        self.children = self.answers
        self.container = None
        self.questionnaire = None
        self.validation = None
        self.questionnaire = None
        self.templatable_properties = ['title', 'description']
        self.display = Display()
        self.type = None

    def add_answer(self, answer):
        if answer not in self.answers:
            self.answers.append(answer)
            answer.container = self
