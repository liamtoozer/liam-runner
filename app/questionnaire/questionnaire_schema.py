import collections
import itertools
from app.validation.error_messages import error_messages


class QuestionnaireSchema(object):  # pylint: disable=too-many-public-methods
    def __init__(self, questionnaire_json):
        self.json = questionnaire_json
        self._parse_schema()

    @property
    def sections(self):
        return self._sections_by_id.values()

    @property
    def groups(self):
        return self._groups_by_id.values()

    @property
    def blocks(self):
        return self._blocks_by_id.values()

    @property
    def questions(self):
        return self._questions_by_id.values()

    @property
    def answers(self):
        return self._answers_by_id.values()

    def get_section(self, section_id):
        return self._sections_by_id.get(section_id)

    def get_group(self, group_id):
        return self._groups_by_id.get(group_id)

    def get_block(self, block_id):
        return self._blocks_by_id.get(block_id)

    def get_question(self, question_id):
        return self._questions_by_id.get(question_id)

    def get_answer(self, answer_id):
        return self._answers_by_id.get(answer_id)

    def get_groups_that_repeat_with_answer_id(self, answer_id):
        for group in self.groups:
            repeating_rule = self.get_repeat_rule(group)
            if repeating_rule and repeating_rule['answer_id'] == answer_id:
                yield group

    def group_has_questions(self, group_id):
        for block in self.get_group(group_id)['blocks']:
            if block['type'] == 'Question':
                return True

        return False

    def get_first_block_id_for_group(self, group_id):
        group = self.get_group(group_id)
        if group:
            return group['blocks'][0]['id']

    def get_answer_ids_for_group(self, group_id):
        answer_ids = []
        group = self.get_group(group_id)
        for block in group['blocks']:
            answer_ids.extend(self.get_answer_ids_for_block(block['id']))

        return answer_ids

    def get_answers_by_id_for_block(self, block_id):
        block = self.get_block(block_id)
        if block:
            answer_lists = (
                question.get('answers', [])
                for question in block.get('questions', [])
            )
            return {
                answer['id']: answer
                for answer in itertools.chain.from_iterable(answer_lists)
            }

        return {}

    def get_answer_ids_for_block(self, block_id):
        return list(self.get_answers_by_id_for_block(block_id).keys())

    def get_answers_for_block(self, block_id):
        return list(self.get_answers_by_id_for_block(block_id).values())

    def get_answers_that_repeat_in_block(self, block_id):
        block = self.get_block(block_id)

        for question in block.get('questions', []):
            if question['type'] == 'RepeatingAnswer':
                for answer in question['answers']:
                    yield answer

    def get_summary_and_confirmation_blocks(self):
        return [
            block['id'] for block in self.blocks
            if block['type'] in ('Summary', 'Confirmation')
        ]

    def get_parent_options_for_block(self, block_id):
        options_with_children = {}

        for answer_json in self.get_answers_for_block(block_id):
            if answer_json['type'] in ['Checkbox', 'Radio']:
                answer_options_with_children = {
                    answer_json['id']: {
                        'index': index,
                        'child_answer_id': o['child_answer_id'],
                    }
                    for index, o in enumerate(answer_json['options']) if 'child_answer_id' in o}

                options_with_children.update(answer_options_with_children)
        return options_with_children

    @staticmethod
    def get_repeat_rule(group):
        if 'routing_rules' in group:
            for rule in group['routing_rules']:
                if 'repeat' in rule.keys():
                    return rule['repeat']

    @staticmethod
    def get_questions_for_block(block_json):
        for question_json in block_json.get('questions', []):
            yield question_json

    def _parse_schema(self):
        self._sections_by_id = self._get_sections_by_id()
        self._groups_by_id = get_nested_schema_objects(self._sections_by_id, 'groups')
        self._blocks_by_id = get_nested_schema_objects(self._groups_by_id, 'blocks')
        self._questions_by_id = get_nested_schema_objects(self._blocks_by_id, 'questions')
        self._answers_by_id = get_nested_schema_objects(self._questions_by_id, 'answers')
        self.error_messages = self._get_error_messages()
        self.aliases = self._get_aliases()

    def _get_sections_by_id(self):
        return collections.OrderedDict(
            (section['id'], section)
            for section in self.json.get('sections', [])
        )

    def _get_error_messages(self):
        messages = error_messages.copy()
        if 'messages' in self.json:
            messages.update(self.json['messages'])

        return messages

    def _get_aliases(self):
        aliases = {}
        for question in self.questions:
            for answer in question.get('answers', []):
                if 'alias' in answer:
                    if answer['alias'] in aliases:
                        raise Exception(
                            'Duplicate alias found: ' + answer['alias'])
                    aliases[answer['alias']] = {
                        'answer_id': answer['id'],
                        'repeats': answer['type'] == 'Checkbox' or question['type'] == 'RepeatingAnswer',
                    }

        return aliases


def get_nested_schema_objects(parent_object, list_key):
    """
    :param parent_object: dict containing a list
    :param list_key: key of the nested list to extract
    """
    lists = (
        obj.get(list_key, [])
        for obj in parent_object.values()
    )
    return collections.OrderedDict(
        (nested_item['id'], nested_item)
        for nested_item in itertools.chain.from_iterable(lists)
    )