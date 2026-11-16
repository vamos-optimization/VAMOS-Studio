"""Tests for what New run says about populations and many objectives."""

import pytest

from vamos_studio.population_notes import objective_notes, population_notes


class TestPopulationNotes:
    def test_should_name_the_weight_file_of_moead(self):
        # Act
        [(level, text)] = population_notes("moead", {"pop_size": 100}, 3)

        # Assert
        assert level == "caption" and "W3D_100.dat" in text

    def test_should_say_moead_uses_a_lattice_without_a_weight_file(self):
        # Act
        [(level, text)] = population_notes("moead", {"pop_size": 100}, 6)

        # Assert
        assert level == "info"
        assert "lattice of 3 divisions, 56 vectors" in text

    def test_should_give_the_reference_directions_of_nsgaiii(self):
        # Act
        [(level, text)] = population_notes("nsgaiii", {"pop_size": 100}, 8)

        # Assert
        assert level == "caption" and "36 reference directions" in text

    @pytest.mark.parametrize(
        ("divisions", "n_obj", "warning"),
        [(12, 3, None), (12, 2, "is small"), (8, 2, "more divisions"), (8, 8, "is large")],
    )
    def test_should_warn_about_rvea_populations_out_of_range(self, divisions, n_obj, warning):
        # Act
        notes = population_notes("rvea", {"n_partitions": divisions}, n_obj)

        # Assert
        warnings = [text for level, text in notes if level == "warning"]
        assert notes[0][0] == "caption"
        assert (warning is None and not warnings) or any(warning in text for text in warnings)

    def test_should_say_nothing_for_nsgaii(self):
        # Act / Assert
        assert population_notes("nsgaii", {"pop_size": 100}, 3) == []


class TestObjectiveNotes:
    @pytest.mark.parametrize("algorithm", ["nsgaii", "spea2", "smsemoa"])
    def test_should_warn_about_pareto_based_algorithms_with_many_objectives(self, algorithm):
        # Act
        [(level, text)] = objective_notes(algorithm, 6)

        # Assert
        assert level == "warning" and "6" in text

    @pytest.mark.parametrize("algorithm", ["nsgaiii", "moead", "rvea", "agemoea"])
    def test_should_not_warn_about_many_objective_algorithms(self, algorithm):
        # Act / Assert
        assert objective_notes(algorithm, 8) == []

    def test_should_not_warn_with_three_objectives(self):
        # Act / Assert
        assert objective_notes("nsgaii", 3) == []
