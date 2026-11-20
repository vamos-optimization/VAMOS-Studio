"""Tests for NSGA-III and RVEA started from a file of reference vectors (VAMOS 1.5)."""

import dataclasses

import numpy as np
import pytest
from conftest import make_request, wait_for_end
from vamos.resources import weight_path

from vamos_studio.backend import runs, vector_files
from vamos_studio.backend.upstream.vamos_bridge import (
    builtin_space,
    population,
    to_algorithm_config,
)

W3D_91 = weight_path("W3D_91.dat").read_bytes()


class TestChoices:
    def test_should_list_the_files_vamos_ships_for_the_objectives(self):
        # Act
        files = vector_files.packaged_files(3)

        # Assert
        assert {"W3D_91.dat", "W3D_100.dat"} <= set(files)
        assert all(name.startswith("W3D_") for name in files)

    def test_should_count_the_vectors_of_a_packaged_file(self):
        # Act
        spec = vector_files.packaged("W3D_100.dat")

        # Assert
        assert vector_files.count(spec) == 100
        assert vector_files.vectors_of(spec, 3).shape == (100, 3)

    def test_should_refuse_a_file_vamos_does_not_ship(self):
        # Act / Assert
        with pytest.raises(ValueError):
            vector_files.packaged("W3D_7.dat")

    @pytest.mark.parametrize("separator", [" ", ",", "\t"])
    def test_should_read_the_users_file_with_any_separator(self, separator):
        # Arrange
        text = "\n".join(separator.join(row) for row in [("1", "0", "0"), ("0.5", "0.5", "0")])

        # Act
        spec = vector_files.uploaded("mine.txt", text.encode(), 3)

        # Assert
        assert spec["source"] == vector_files.USER_FILE
        assert vector_files.count(spec) == 2

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("0.5 0.5\n", "2 components"),
            ("a b c\n", "not a list of numbers"),
            ("0.2 0.2 0.2\n", "sum to 1"),
            ("-0.5 1 0.5\n", "non-negative"),
            ("\n\n", "no vectors"),
        ],
    )
    def test_should_refuse_a_file_that_is_not_weight_vectors(self, text, message):
        # Act / Assert
        with pytest.raises(ValueError, match=message):
            vector_files.uploaded("bad.txt", text.encode(), 3)

    def test_should_write_the_users_vectors_for_vamos(self, tmp_path):
        # Arrange
        spec = vector_files.uploaded("mine.dat", W3D_91, 3)

        # Act
        path = vector_files.materialize(spec, tmp_path)

        # Assert
        assert np.allclose(np.loadtxt(path), vector_files.vectors_of(spec, 3))


class TestBridge:
    @pytest.mark.parametrize(
        ("algorithm", "field"),
        [("nsgaiii", "reference_directions"), ("rvea", "reference_vectors")],
    )
    def test_should_start_from_the_file_with_one_individual_per_vector(self, algorithm, field):
        # Arrange
        configuration = builtin_space(algorithm, "real").default_configuration()
        path = str(weight_path("W3D_100.dat"))

        # Act
        config = to_algorithm_config(configuration, 12, 3, (path, 100))

        # Assert
        assert config.pop_size == 100
        assert getattr(config, field) == {"path": path}

    def test_should_give_the_population_of_the_file(self):
        # Act / Assert
        assert population({"pop_size": 100}, "rvea", 3, vectors=100) == 100
        assert population({"pop_size": 100}, "rvea", 3) == 91

    def test_should_refuse_vectors_for_an_algorithm_without_them(self):
        # Act / Assert
        with pytest.raises(ValueError, match="does not take"):
            to_algorithm_config(
                builtin_space("nsgaii", "real").default_configuration(), 12, 3, ("x.dat", 10)
            )


class TestRuns:
    @pytest.mark.parametrize(
        ("algorithm", "spec", "field"),
        [
            ("rvea", vector_files.packaged("W3D_100.dat"), "reference_vectors"),
            ("nsgaiii", vector_files.uploaded("mine.dat", W3D_91, 3), "reference_directions"),
        ],
    )
    def test_should_run_from_the_file_and_record_it(self, algorithm, spec, field, tmp_path):
        # Arrange
        space = builtin_space(algorithm, "real")
        request = dataclasses.replace(
            make_request("dtlz2", 3000),
            algorithm=algorithm,
            space=space.name,
            space_hash=space.content_hash(),
            configuration=dict(space.default_configuration().values),
            n_obj=3,
            reference_vectors=spec,
        )

        # Act
        run = runs.launch(request, tmp_path)
        state = wait_for_end(run)

        # Assert
        resolved = runs.manifest(run)["resolved_spec"]["algorithm"]
        assert state == runs.RunState.FINISHED
        assert resolved["config"]["pop_size"] == vector_files.count(spec)
        assert resolved["resolution"][field]["source"] == "file"
        assert runs.read_request(run).reference_vectors == spec
