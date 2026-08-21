from __future__ import annotations

from app.models.assessment_question import AssessmentQuestionType
from app.services.assessment_interaction_palette_service import (
    chemistry_atomic_structure_palette,
    equation_editor_palette,
    get_palette,
    graphing_palette,
    infer_interaction_config,
    list_palette_ids,
    mixed_graph_equation_palette,
)


def test_palette_registry_exposes_expected_stable_ids():
    assert list_palette_ids() == (
        "chemistry.atomic_structure",
        "general.diagram_labelling",
        "general.equation_editor",
        "general.graph_equation",
        "general.graphing",
        "physics.fields_vectors",
    )


def test_atomic_structure_palette_contains_expected_particle_symbols():
    config = chemistry_atomic_structure_palette()

    assert config.mode == "visual_annotation"
    assert config.palette_id == "chemistry.atomic_structure"
    assert config.coordinate_system == "normalized"

    symbols = {
        tool.tool_id: (
            tool.symbol,
            tool.label,
        )
        for tool in config.tools
    }

    assert symbols == {
        "electron": ("×", "Electron"),
        "neutron": ("●", "Neutron"),
        "proton": ("○", "Proton"),
    }


def test_atomic_structure_inference_survives_missing_symbol_glyphs():
    config = infer_interaction_config(
        question_text=(
            "Complete the figure below to show the position of the particles "
            "in an atom of element Z. Use the symbols: electron neutron proton"
        ),
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
    )

    assert config is not None
    assert config.palette_id == "chemistry.atomic_structure"


def test_atomic_structure_inference_requires_diagram_annotation_type():
    config = infer_interaction_config(
        question_text=(
            "Complete the figure to show the particles in an atom. "
            "Use electron proton neutron."
        ),
        question_type=AssessmentQuestionType.WRITTEN,
    )

    assert config is None


def test_graphing_inference_proposes_graph_palette():
    config = infer_interaction_config(
        question_text=(
            "Plot the graph of current against potential difference and draw "
            "a line of best fit. Label the axes."
        ),
        question_type=AssessmentQuestionType.DIAGRAM_ANNOTATION,
    )

    assert config is not None
    assert config.palette_id == "general.graphing"
    assert config.coordinate_system == "graph"
    assert config.snap_to_grid is True


def test_equation_inference_proposes_equation_editor_for_written_question():
    config = infer_interaction_config(
        question_text=(
            "Use the equation for density and rearrange the equation to make "
            "area the subject. Show your algebra."
        ),
        question_type=AssessmentQuestionType.WRITTEN,
    )

    assert config is not None
    assert config.palette_id == "general.equation_editor"
    assert config.mode == "equation"
    assert config.allow_equation_rearrangement is True
    assert config.allow_equation_steps is True


def test_graph_and_equation_terms_propose_mixed_palette():
    config = infer_interaction_config(
        question_text=(
            "Plot a graph of mass against volume. Use the equation for density "
            "to calculate the gradient and show your algebra."
        ),
        question_type=AssessmentQuestionType.WRITTEN,
    )

    assert config is not None
    assert config.palette_id == "general.graph_equation"
    assert config.mode == "mixed"


def test_equation_palette_contains_editor_and_manipulation_tools():
    config = equation_editor_palette()

    tool_types = {
        tool.tool_type.value
        for tool in config.tools
    }

    assert "equation_editor" in tool_types
    assert "equation_manipulation" in tool_types


def test_graph_palette_contains_plotting_and_axis_tools():
    config = graphing_palette()

    tool_types = {
        tool.tool_type.value
        for tool in config.tools
    }

    assert "plot_point" in tool_types
    assert "line" in tool_types
    assert "curve" in tool_types
    assert "axis_label" in tool_types


def test_mixed_palette_contains_graph_and_equation_capabilities():
    config = mixed_graph_equation_palette()

    tool_types = {
        tool.tool_type.value
        for tool in config.tools
    }

    assert "plot_point" in tool_types
    assert "axis_label" in tool_types
    assert "equation_editor" in tool_types
    assert "equation_manipulation" in tool_types


def test_get_palette_rejects_unknown_id():
    try:
        get_palette(
            "unknown.palette",
        )
    except ValueError as exc:
        assert "Unsupported assessment interaction palette" in str(exc)
    else:
        raise AssertionError("Unknown palette id should have raised ValueError.")
