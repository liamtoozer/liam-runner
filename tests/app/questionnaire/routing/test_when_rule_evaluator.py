from datetime import datetime, timezone
from typing import Optional, Union
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from app.data_models import AnswerStore, ListStore
from app.data_models.answer import Answer
from app.questionnaire import Location, QuestionnaireSchema
from app.questionnaire.relationship_location import RelationshipLocation
from app.questionnaire.routing.operator import Operator
from app.questionnaire.routing.when_rule_evaluator import WhenRuleEvaluator
from tests.app.questionnaire.test_value_source_resolver import get_list_items

current_date = datetime.now(timezone.utc).date()
current_date_as_yyyy_mm_dd = current_date.strftime("%Y-%m-%d")


def get_mock_schema():
    schema = Mock(
        QuestionnaireSchema(
            {
                "questionnaire_flow": {
                    "type": "Linear",
                    "options": {"summary": {"collapsible": False}},
                }
            }
        )
    )
    return schema


def get_when_rule_evaluator(
    schema: QuestionnaireSchema = None,
    answer_store: AnswerStore = AnswerStore(),
    list_store: ListStore = ListStore(),
    metadata: Optional[dict] = None,
    location: Union[Location, RelationshipLocation] = Location(
        section_id="test-section", block_id="test-block"
    ),
    routing_path_block_ids: Optional[list] = None,
):
    if not schema:
        schema = get_mock_schema()
        schema.is_repeating_answer = Mock(return_value=True)
        schema.get_default_answer = Mock(return_value=None)

    return WhenRuleEvaluator(
        schema=schema,
        metadata=metadata or {},
        answer_store=answer_store,
        list_store=list_store,
        location=location,
        routing_path_block_ids=routing_path_block_ids,
    )


@pytest.mark.parametrize(
    "rule, expected_result",
    [
        # Test True
        ({Operator.NOT: [False]}, True),
        ({Operator.AND: [True, True]}, True),
        ({Operator.OR: [True, False]}, True),
        ({Operator.EQUAL: ["Yes", "Yes"]}, True),
        ({Operator.NOT_EQUAL: ["Yes", "No"]}, True),
        ({Operator.GREATER_THAN: [3, 1]}, True),
        ({Operator.GREATER_THAN_OR_EQUAL: [1, 1]}, True),
        ({Operator.LESS_THAN: [0.5, 1]}, True),
        ({Operator.LESS_THAN_OR_EQUAL: [0.5, 0.5]}, True),
        ({Operator.IN: ["Yes", ["Yes"]]}, True),
        ({Operator.ANY_IN: [["Yes"], ["Yes", "No"]]}, True),
        ({Operator.ALL_IN: [["Yes", "No"], ["Yes", "No"]]}, True),
        # Test False
        ({Operator.NOT: [True]}, False),
        ({Operator.AND: [True, False]}, False),
        ({Operator.OR: [False, False]}, False),
        ({Operator.EQUAL: ["Yes", "No"]}, False),
        ({Operator.NOT_EQUAL: ["Yes", "Yes"]}, False),
        ({Operator.GREATER_THAN: [1, 3]}, False),
        ({Operator.GREATER_THAN_OR_EQUAL: [0.5, 1]}, False),
        ({Operator.LESS_THAN: [1, 0.5]}, False),
        ({Operator.LESS_THAN_OR_EQUAL: [1, 0.5]}, False),
        ({Operator.IN: ["No", ["Yes"]]}, False),
        ({Operator.ANY_IN: [["Maybe"], ["Yes", "No"]]}, False),
        ({Operator.ALL_IN: [["Yes", "Maybe"], ["Yes", "No"]]}, False),
    ],
)
def test_boolean_operators_as_rule(rule, expected_result):
    when_rule_evaluator = get_when_rule_evaluator()
    assert when_rule_evaluator.evaluate(rule=rule) is expected_result


@pytest.mark.parametrize(
    "answer_value, expected_result",
    [(3, True), (7, False)],
)
def test_answer_source(answer_value, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore([{"answer_id": "some-answer", "value": answer_value}]),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [{"source": "answers", "identifier": "some-answer"}, 3]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "answer_value, expected_result",
    [(3, True), (7, False)],
)
def test_answer_source_with_list_item_selector_location(answer_value, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "some-answer",
                    "list_item_id": "item-1",
                    "value": answer_value,
                }
            ]
        ),
        location=Location(
            section_id="some-section", block_id="some-block", list_item_id="item-1"
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {
                        "source": "answers",
                        "identifier": "some-answer",
                        "list_item_selector": {
                            "source": "location",
                            "id": "list_item_id",
                        },
                    },
                    3,
                ]
            },
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "answer_value, expected_result",
    [(3, True), (7, False)],
)
def test_answer_source_with_list_item_selector_list_first_item(
    answer_value, expected_result
):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "some-answer",
                    "list_item_id": "item-1",
                    "value": answer_value,
                }
            ]
        ),
        list_store=ListStore([{"name": "some-list", "items": get_list_items(3)}]),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {
                        "source": "answers",
                        "identifier": "some-answer",
                        "list_item_selector": {
                            "source": "list",
                            "id": "some-list",
                            "id_selector": "first",
                        },
                    },
                    3,
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "answer_value, expected_result",
    [(3, True), (7, False)],
)
def test_answer_source_with_dict_answer_selector(answer_value, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "some-answer",
                    "value": {"years": answer_value, "months": 10},
                }
            ]
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {
                        "source": "answers",
                        "identifier": "some-answer",
                        "selector": "years",
                    },
                    3,
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "metadata_value, expected_result",
    [(3, True), (7, False)],
)
def test_metadata_source(metadata_value, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        metadata={"some-metadata": metadata_value},
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {"source": "metadata", "identifier": "some-metadata"},
                    3,
                ]
            },
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "list_count, expected_result",
    [(3, True), (7, False)],
)
def test_list_source(list_count, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        list_store=ListStore(
            [{"name": "some-list", "items": get_list_items(list_count)}]
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={Operator.EQUAL: [{"source": "list", "identifier": "some-list"}, 3]}
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "list_item_id, expected_result",
    [("item-1", True), ("item-2", False)],
)
def test_list_source_with_id_selector_first(list_item_id, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        list_store=ListStore([{"name": "some-list", "items": get_list_items(1)}]),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {
                        "source": "list",
                        "identifier": "some-list",
                        "id_selector": "first",
                    },
                    list_item_id,
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "list_item_id, expected_result",
    [("item-1", True), ("item-2", True), ("item-3", True), ("item-4", False)],
)
def test_list_source_with_id_selector_same_name_items(list_item_id, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        list_store=ListStore(
            [
                {
                    "name": "some-list",
                    "items": get_list_items(5),
                    "same_name_items": get_list_items(3),
                }
            ]
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.IN: [
                    list_item_id,
                    {
                        "source": "list",
                        "identifier": "some-list",
                        "id_selector": "same_name_items",
                    },
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "primary_person_list_item_id, expected_result",
    [("item-1", True), ("item-2", False)],
)
def test_list_source_id_selector_primary_person(
    primary_person_list_item_id, expected_result
):
    location = RelationshipLocation(
        section_id="some-section",
        block_id="some-block",
        list_item_id="item-1",
        to_list_item_id="item-2",
        list_name="household",
    )

    when_rule_evaluator = get_when_rule_evaluator(
        list_store=ListStore(
            [
                {
                    "name": "some-list",
                    "primary_person": primary_person_list_item_id,
                    "items": get_list_items(3),
                }
            ]
        ),
        location=location,
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {
                        "source": "list",
                        "identifier": "some-list",
                        "id_selector": "primary_person",
                    },
                    {"source": "location", "identifier": "list_item_id"},
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "list_item_id, expected_result",
    [("item-1", True), ("item-2", False)],
)
def test_current_location_source(list_item_id, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        location=Location(
            section_id="some-section", block_id="some-block", list_item_id=list_item_id
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {"source": "location", "identifier": "list_item_id"},
                    "item-1",
                ]
            }
        )
        is expected_result
    )


@pytest.mark.parametrize(
    "operator, operands, expected_result",
    [
        (
            Operator.AND,
            [
                {
                    Operator.EQUAL: [
                        {"source": "answers", "identifier": "answer-1"},
                        "Yes, I do",
                    ]
                },
                {
                    Operator.GREATER_THAN_OR_EQUAL: [
                        {
                            "source": "answers",
                            "identifier": "answer-2",
                            "list_item_selector": {
                                "source": "location",
                                "id": "list_item_id",
                            },
                        },
                        9,
                    ]
                },
                {
                    Operator.OR: [
                        {
                            Operator.EQUAL: [
                                {"source": "list", "identifier": "some-list"},
                                0,
                            ]
                        },
                        {
                            Operator.AND: [
                                {
                                    Operator.NOT: [
                                        {
                                            Operator.IN: [
                                                {
                                                    "source": "metadata",
                                                    "identifier": "region_code",
                                                },
                                                ["GB-ENG", "GB-WLS"],
                                            ]
                                        }
                                    ]
                                },
                                {
                                    Operator.IN: [
                                        {
                                            "source": "list",
                                            "identifier": "some-list",
                                            "id_selector": "first",
                                        },
                                        {
                                            "source": "list",
                                            "identifier": "some-list",
                                            "id_selector": "same_name_items",
                                        },
                                    ]
                                },
                            ]
                        },
                    ]
                },
            ],
            True,
        )
    ],
)
def test_nested_rules(operator, operands, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "answer-1",
                    "list_item_id": "item-1",
                    "value": "Yes, I do",
                },
                {
                    "answer_id": "answer-2",
                    "list_item_id": "item-1",
                    "value": 10,
                },
            ]
        ),
        metadata={"region_code": "GB-NIR", "language_code": "en"},
        list_store=ListStore(
            [
                {
                    "name": "some-list",
                    "items": get_list_items(5),
                    "same_name_items": get_list_items(3),
                }
            ],
        ),
        location=Location(
            section_id="some-section", block_id="some-block", list_item_id="item-1"
        ),
    )

    assert when_rule_evaluator.evaluate(rule={operator: operands}) is expected_result


@pytest.mark.parametrize(
    "operands",
    [
        [None, 10],
        [10, None],
        [None, None],
        # Value for these Value Sources does not exist
        [10, {"source": "answers", "identifier": "some-answer"}],
        [10, {"source": "metadata", "identifier": "some-metadata"}],
    ],
)
@pytest.mark.parametrize(
    "operator_name",
    [
        Operator.GREATER_THAN,
        Operator.GREATER_THAN_OR_EQUAL,
        Operator.LESS_THAN,
        Operator.LESS_THAN_OR_EQUAL,
    ],
)
def test_comparison_operator_rule_with_nonetype_operands(operator_name, operands):
    when_rule_evaluator = get_when_rule_evaluator()
    assert when_rule_evaluator.evaluate(rule={operator_name: operands}) is False


@pytest.mark.parametrize(
    "operands",
    [
        [None, ["Yes"]],
        [["Yes"], None],
        [None, None],
        # Value for value sources does not exist
        [["Yes"], {"source": "answers", "identifier": "some-answer"}],
        [["Yes"], {"source": "metadata", "identifier": "some-metadata"}],
    ],
)
@pytest.mark.parametrize(
    "operator_name", [Operator.ALL_IN, Operator.ANY_IN, Operator.IN]
)
def test_array_operator_rule_with_nonetype_operands(operator_name, operands):
    when_rule_evaluator = get_when_rule_evaluator()
    assert (
        when_rule_evaluator.evaluate(
            rule={operator_name: operands},
        )
        is False
    )


@freeze_time(current_date)
@pytest.mark.parametrize(
    "rule, expected_result",
    [
        # Test True
        (
            {
                Operator.EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                ]
            },
            True,
        ),
        (
            {
                Operator.NOT_EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"days": -1}]},
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                ]
            },
            True,
        ),
        (
            {
                Operator.LESS_THAN: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"days": -1}]},
                    {Operator.DATE: ["now"]},
                ]
            },
            True,
        ),
        (
            {
                Operator.LESS_THAN_OR_EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"days": -1}]},
                    {Operator.DATE: ["now", {"days": -1}]},
                ]
            },
            True,
        ),
        (
            {
                Operator.GREATER_THAN: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                    {Operator.DATE: ["now", {"months": -1}]},
                ]
            },
            True,
        ),
        (
            {
                Operator.GREATER_THAN_OR_EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"months": -1}]},
                    {Operator.DATE: ["now", {"months": -1}]},
                ]
            },
            True,
        ),
        # Test False
        (
            {
                Operator.EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"days": -1}]},
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                ]
            },
            False,
        ),
        (
            {
                Operator.NOT_EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                ]
            },
            False,
        ),
        (
            {
                Operator.LESS_THAN: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"days": 1}]},
                    {Operator.DATE: ["now"]},
                ]
            },
            False,
        ),
        (
            {
                Operator.GREATER_THAN: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd, {"months": -1}]},
                    {Operator.DATE: ["now"]},
                ]
            },
            False,
        ),
        (
            {
                Operator.EQUAL: [
                    {Operator.DATE: [current_date_as_yyyy_mm_dd]},
                    {Operator.DATE: [None]},
                ]
            },
            False,
        ),
    ],
)
def test_date_value(rule, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "some-answer",
                    "value": current_date_as_yyyy_mm_dd,
                }
            ]
        ),
        metadata={"some-metadata": current_date_as_yyyy_mm_dd},
    )

    assert (
        when_rule_evaluator.evaluate(
            rule=rule,
        )
        is expected_result
    )


def test_answer_source_outside_of_repeating_section():
    schema = get_mock_schema()

    schema.is_repeating_answer = Mock(return_value=False)
    answer_store = AnswerStore([{"answer_id": "some-answer", "value": "Yes"}])

    when_rule_evaluator = get_when_rule_evaluator(
        schema=schema,
        answer_store=answer_store,
        location=Location(
            section_id="some-section", block_id="some-block", list_item_id="item-1"
        ),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {"source": "answers", "identifier": "some-answer"},
                    "Yes",
                ]
            }
        )
        is True
    )


@pytest.mark.parametrize("is_answer_on_path", [True, False])
def test_answer_source_not_on_path_non_repeating_section(is_answer_on_path):
    schema = get_mock_schema()

    location = Location(section_id="test-section", block_id="test-block")

    if is_answer_on_path:
        schema.get_block_for_answer_id = Mock(return_value={"id": f"block-on-path"})
        answer_id = "answer-on-path"
        expected_result = True
    else:
        schema.get_block_for_answer_id = Mock(return_value={"id": f"block-not-on-path"})
        answer_id = "answer-not-on-path"
        expected_result = False

    answer = Answer(answer_id=answer_id, value="Yes")

    when_rule_evaluator = get_when_rule_evaluator(
        schema=schema,
        answer_store=AnswerStore([answer.to_dict()]),
        location=location,
        routing_path_block_ids=["block-on-path"],
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    "Yes",
                    {"source": "answers", "identifier": "answer-on-path"},
                ]
            }
        )
        == expected_result
    )


@pytest.mark.parametrize("is_answer_on_path", [True, False])
def test_answer_source_not_on_path_repeating_section(is_answer_on_path):
    schema = get_mock_schema()
    schema.is_repeating_answer = Mock(return_value=True)
    location = Location(
        section_id="test-section", block_id="test-block", list_item_id="item-1"
    )

    if is_answer_on_path:
        schema.get_block_for_answer_id = Mock(return_value={"id": f"block-on-path"})
        answer_id = "answer-on-path"
        expected_result = True
    else:
        schema.get_block_for_answer_id = Mock(return_value={"id": f"block-not-on-path"})
        answer_id = "answer-not-on-path"
        expected_result = False

    answer = Answer(answer_id=answer_id, list_item_id="item-1", value="Yes")

    when_rule_evaluator = get_when_rule_evaluator(
        schema=schema,
        answer_store=AnswerStore([answer.to_dict()]),
        location=location,
        routing_path_block_ids=["block-on-path"],
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    "Yes",
                    {"source": "answers", "identifier": "answer-on-path"},
                ]
            }
        )
        == expected_result
    )


@pytest.mark.parametrize("comparison_value, expected_result", [(3, True), (7, False)])
def test_answer_source_default_answer_used_when_no_answer(
    comparison_value, expected_result
):
    schema = get_mock_schema()
    schema.get_default_answer = Mock(
        return_value=Answer(answer_id="answer-that-does-not-exist", value=3)
    )

    when_rule_evaluator = get_when_rule_evaluator(
        schema=schema,
        answer_store=AnswerStore([{"answer_id": f"some-answer", "value": "No"}]),
    )

    assert (
        when_rule_evaluator.evaluate(
            rule={
                Operator.EQUAL: [
                    {"source": "answers", "identifier": "answer-that-does-not-exist"},
                    comparison_value,
                ]
            }
        )
        is expected_result
    )


def test_raises_exception_when_bad_operand_type():
    with pytest.raises(TypeError):
        when_rule_evaluator = get_when_rule_evaluator()
        when_rule_evaluator.evaluate(rule={Operator.EQUAL: {1, 1}})


@pytest.mark.parametrize(
    "rule, expected_result",
    [
        (
            {
                Operator.EQUAL: [
                    {
                        Operator.COUNT: [
                            {"source": "answers", "identifier": "some-answer"}
                        ]
                    },
                    2,
                ]
            },
            True,
        ),
    ],
)
def test_answer_source_count(rule, expected_result):
    when_rule_evaluator = get_when_rule_evaluator(
        answer_store=AnswerStore(
            [
                {
                    "answer_id": "some-answer",
                    "value": ["array element 1", "array element 2"],
                }
            ]
        ),
    )
    assert when_rule_evaluator.evaluate(rule=rule) is expected_result