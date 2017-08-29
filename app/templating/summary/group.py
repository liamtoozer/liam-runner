from app.templating.summary.block import Block


class Group:

    def __init__(self, group_schema, answers_map, path, answer_store, metadata, url_for):
        self.id = group_schema['id']
        self.title = group_schema['title']
        self.blocks = self._build_blocks(group_schema, answers_map, path, answer_store, metadata, url_for)

    @staticmethod
    def _build_blocks(group_schema, answers_map, path, answer_store, metadata, url_for):
        blocks = []

        for block in group_schema['blocks']:
            if block['id'] in [location.block_id for location in path] and \
                    block['type'] == 'Questionnaire':
                blocks.extend([Block(block, answers_map, group_schema['id'], answer_store, metadata, url_for)])

        return blocks