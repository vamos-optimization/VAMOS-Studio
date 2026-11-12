"""Tests for the grammar model of parameter spaces (no VAMOS needed)."""

import copy

import pytest

from vamos_studio.backend.upstream.parameter_space import (
    ParameterSpaceError,
    same_value,
    space_from_dict,
    space_from_yaml,
)

DOCUMENT = {
    "schema": "vamos.parameter-space",
    "schema_version": "1.0.0",
    "name": "toy_real",
    "algorithm": "toy",
    "encoding": "real",
    "parameters": {
        "size": {"type": "int", "default": 10, "range": [2, 50]},
        "crossover": {
            "type": "categorical",
            "default": "sbx",
            "global_sub_parameters": {
                "crossover_prob": {"type": "real", "default": 0.9, "range": [0.0, 1.0]}
            },
            "values": {
                "sbx": {
                    "conditional_parameters": {
                        "eta": {"type": "real", "default": 20.0, "range": [5.0, 40.0]}
                    }
                },
                "arithmetic": {},
            },
        },
        "elitist": {"type": "boolean", "default": True},
        "ratio": {"type": "categorical", "default": 1.0, "values": [0.5, 1.0]},
    },
}


@pytest.fixture
def document() -> dict:
    return copy.deepcopy(DOCUMENT)


@pytest.fixture
def space(document):
    return space_from_dict(document)


class TestSameValue:
    @pytest.mark.parametrize(
        ("left", "right", "expected"),
        [(1, 1.0, True), (True, 1, False), (True, True, True), ("a", "a", True), (0, False, False)],
    )
    def test_should_tell_booleans_apart_from_numbers(self, left, right, expected):
        # Act
        result = same_value(left, right)

        # Assert
        assert result is expected


class TestLoading:
    def test_should_keep_the_depth_first_order_of_every_parameter(self, space):
        # Act
        names = [parameter.name for parameter in space.all_parameters()]

        # Assert
        assert names == ["size", "crossover", "crossover_prob", "eta", "elitist", "ratio"]

    def test_should_survive_a_round_trip_through_yaml(self, space):
        # Act
        reloaded = space_from_yaml(space.to_yaml())

        # Assert
        assert reloaded == space
        assert reloaded.content_hash() == space.content_hash()

    def test_should_change_the_hash_when_the_space_changes(self, space, document):
        # Arrange
        document["parameters"]["size"]["range"] = [2, 60]

        # Act
        changed = space_from_dict(document)

        # Assert
        assert changed.content_hash() != space.content_hash()

    @pytest.mark.parametrize(
        ("field", "value"),
        [("schema", "other.schema"), ("schema_version", "9.9.9")],
    )
    def test_should_reject_an_unknown_schema(self, document, field, value):
        # Arrange
        document[field] = value

        # Act / Assert
        with pytest.raises(ParameterSpaceError):
            space_from_dict(document)


class TestValidation:
    @pytest.mark.parametrize(
        ("path", "body", "rule"),
        [
            (("size",), {"type": "int", "default": 99, "range": [2, 50]}, "G3"),
            (("size",), {"type": "int", "default": 10, "range": [50, 2]}, "G4"),
            (("size",), {"type": "int", "default": 10, "range": [2.5, 50]}, "G4"),
            (("size",), {"type": "real", "default": 1.0, "range": [0.0, 2.0], "log": True}, "G4"),
            (("ratio",), {"type": "categorical", "default": 0.75, "values": [0.5, 1.0]}, "G3"),
            (("ratio",), {"type": "categorical", "default": 1.0, "values": [1.0, 1]}, "G5"),
            (("elitist",), {"type": "boolean", "default": 1}, "G3"),
        ],
    )
    def test_should_reject_a_parameter_that_breaks_a_rule(self, document, path, body, rule):
        # Arrange
        document["parameters"][path[0]] = body

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match=rule):
            space_from_dict(document)

    def test_should_reject_a_name_used_twice(self, document):
        # Arrange
        document["parameters"]["crossover"]["values"]["arithmetic"] = {
            "conditional_parameters": {"size": {"type": "int", "default": 3, "range": [1, 5]}}
        }

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="G1"):
            space_from_dict(document)

    def test_should_reject_a_name_that_is_not_snake_case(self, document):
        # Arrange
        document["parameters"]["crossoverProbability"] = document["parameters"].pop("size")

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="G1"):
            space_from_dict(document)

    def test_should_require_a_default_for_every_parameter(self, document):
        # Arrange
        del document["parameters"]["crossover"]["values"]["sbx"]["conditional_parameters"]["eta"][
            "default"
        ]

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="default"):
            space_from_dict(document)


class TestConfigurations:
    def test_should_derive_the_default_configuration_from_the_defaults(self, space):
        # Act
        configuration = space.default_configuration()

        # Assert
        assert dict(configuration.values) == {
            "size": 10,
            "crossover": "sbx",
            "crossover_prob": 0.9,
            "eta": 20.0,
            "elitist": True,
            "ratio": 1.0,
        }

    def test_should_drop_the_parameters_of_values_not_chosen(self, space):
        # Arrange
        values = {"size": 10, "crossover": "arithmetic", "crossover_prob": 0.5}
        values |= {"elitist": False, "ratio": 0.5}

        # Act
        configuration = space.configuration(values)

        # Assert
        assert "eta" not in configuration.values
        assert configuration.to_cli() == (
            "--size 10 --crossover arithmetic --crossover_prob 0.5 --elitist false --ratio 0.5"
        )

    def test_should_store_a_real_value_as_a_float(self, space):
        # Arrange
        values = space.default_values() | {"crossover_prob": 1}

        # Act
        configuration = space.configuration(values, complete=True)

        # Assert
        assert isinstance(configuration.values["crossover_prob"], float)

    def test_should_reject_a_value_for_an_inactive_parameter(self, space):
        # Arrange
        values = {"size": 10, "crossover": "arithmetic", "crossover_prob": 0.5, "eta": 20.0}
        values |= {"elitist": False, "ratio": 0.5}

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="not active"):
            space.configuration(values)

    @pytest.mark.parametrize(
        ("name", "value"), [("eta", 99.0), ("crossover", "pcx"), ("size", 3.5), ("elitist", 1)]
    )
    def test_should_reject_a_value_outside_its_domain(self, space, name, value):
        # Arrange
        values = space.default_values() | {name: value}

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="domain"):
            space.configuration(values, complete=True)

    def test_should_reject_a_missing_active_parameter(self, space):
        # Arrange
        values = {"size": 10, "crossover": "sbx", "crossover_prob": 0.5}

        # Act / Assert
        with pytest.raises(ParameterSpaceError, match="Missing"):
            space.configuration(values)

    def test_should_name_the_space_and_its_hash_in_its_document(self, space):
        # Act
        document = space.default_configuration().to_dict()

        # Assert
        assert document["schema"] == "vamos.parameter-configuration"
        assert document["space"] == {
            "name": "toy_real",
            "schema_version": "1.0.0",
            "hash": space.content_hash(),
        }
