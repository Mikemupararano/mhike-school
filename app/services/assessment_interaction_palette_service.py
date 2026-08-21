from __future__ import annotations

import re
from collections.abc import Callable

from app.models.assessment_question import AssessmentQuestionType
from app.schemas.assessment import (
    AssessmentInteractionToolConfig,
    AssessmentInteractionToolType,
    AssessmentQuestionInteractionConfig,
)


def _normalise_text(value: str | None) -> str:
    """
    Return lower-cased, whitespace-normalised text for conservative inference.
    """

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip().lower()


def _tool(
    *,
    tool_id: str,
    tool_type: AssessmentInteractionToolType,
    label: str,
    symbol: str | None = None,
    subject: str | None = None,
) -> AssessmentInteractionToolConfig:
    """
    Build one validated interaction tool.
    """

    return AssessmentInteractionToolConfig(
        tool_id=tool_id,
        tool_type=tool_type,
        label=label,
        symbol=symbol,
        subject=subject,
    )


def chemistry_atomic_structure_palette() -> AssessmentQuestionInteractionConfig:
    """
    Palette for atom-particle placement questions.

    Unicode symbols match common UK examination-paper conventions while labels
    make the meaning explicit to the learner.
    """

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="visual_annotation",
        palette_id="chemistry.atomic_structure",
        palette_label="Atomic structure",
        coordinate_system="normalized",
        snap_to_grid=False,
        tools=[
            _tool(
                tool_id="electron",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Electron",
                symbol="×",
                subject="chemistry",
            ),
            _tool(
                tool_id="neutron",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Neutron",
                symbol="●",
                subject="chemistry",
            ),
            _tool(
                tool_id="proton",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Proton",
                symbol="○",
                subject="chemistry",
            ),
        ],
        allow_undo=True,
        allow_clear=True,
    )


def physics_field_palette() -> AssessmentQuestionInteractionConfig:
    """
    Common field/vector annotation palette for physics diagrams.
    """

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="visual_annotation",
        palette_id="physics.fields_vectors",
        palette_label="Fields and vectors",
        coordinate_system="normalized",
        snap_to_grid=False,
        tools=[
            _tool(
                tool_id="field_into_page",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Field into page",
                symbol="×",
                subject="physics",
            ),
            _tool(
                tool_id="field_out_of_page",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Field out of page",
                symbol="•",
                subject="physics",
            ),
            _tool(
                tool_id="arrow",
                tool_type=AssessmentInteractionToolType.ARROW,
                label="Arrow / vector",
                subject="physics",
            ),
            _tool(
                tool_id="text_label",
                tool_type=AssessmentInteractionToolType.TEXT_LABEL,
                label="Label",
                subject="physics",
            ),
        ],
        allow_undo=True,
        allow_clear=True,
    )


def graphing_palette() -> AssessmentQuestionInteractionConfig:
    """
    Generic graph-response palette suitable across sciences and mathematics.
    """

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="visual_annotation",
        palette_id="general.graphing",
        palette_label="Graphing",
        coordinate_system="graph",
        snap_to_grid=True,
        tools=[
            _tool(
                tool_id="plot_cross",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Plot cross",
                symbol="×",
            ),
            _tool(
                tool_id="plot_point",
                tool_type=AssessmentInteractionToolType.PLOT_POINT,
                label="Plot point",
            ),
            _tool(
                tool_id="straight_line",
                tool_type=AssessmentInteractionToolType.LINE,
                label="Straight line",
            ),
            _tool(
                tool_id="curve",
                tool_type=AssessmentInteractionToolType.CURVE,
                label="Curve",
            ),
            _tool(
                tool_id="axis_label",
                tool_type=AssessmentInteractionToolType.AXIS_LABEL,
                label="Axis label",
            ),
            _tool(
                tool_id="text_label",
                tool_type=AssessmentInteractionToolType.TEXT_LABEL,
                label="Graph label",
            ),
        ],
        allow_undo=True,
        allow_clear=True,
    )


def general_diagram_labelling_palette() -> AssessmentQuestionInteractionConfig:
    """
    Generic cross-subject palette for labelling and marking diagrams.
    """

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="visual_annotation",
        palette_id="general.diagram_labelling",
        palette_label="Diagram labelling",
        coordinate_system="normalized",
        snap_to_grid=False,
        tools=[
            _tool(
                tool_id="cross",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Cross",
                symbol="×",
            ),
            _tool(
                tool_id="dot",
                tool_type=AssessmentInteractionToolType.SYMBOL,
                label="Dot",
                symbol="•",
            ),
            _tool(
                tool_id="arrow",
                tool_type=AssessmentInteractionToolType.ARROW,
                label="Arrow",
            ),
            _tool(
                tool_id="leader_line",
                tool_type=AssessmentInteractionToolType.LEADER_LINE,
                label="Leader line",
            ),
            _tool(
                tool_id="text_label",
                tool_type=AssessmentInteractionToolType.TEXT_LABEL,
                label="Text label",
            ),
        ],
        allow_undo=True,
        allow_clear=True,
    )


def equation_editor_palette(
    *,
    allow_rearrangement: bool = True,
    allow_substitution: bool = True,
    allow_simplification: bool = True,
    allow_steps: bool = True,
) -> AssessmentQuestionInteractionConfig:
    """
    Generic equation-entry/manipulation palette.

    The client may render this using a dedicated maths/equation editor. LaTeX is
    the canonical interchange representation; the learner's step sequence
    should be retained rather than reducing the response to only a final value.
    """

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="equation",
        palette_id="general.equation_editor",
        palette_label="Equation editor",
        coordinate_system="normalized",
        snap_to_grid=False,
        tools=[
            _tool(
                tool_id="equation_editor",
                tool_type=AssessmentInteractionToolType.EQUATION_EDITOR,
                label="Equation editor",
            ),
            _tool(
                tool_id="equation_manipulation",
                tool_type=AssessmentInteractionToolType.EQUATION_MANIPULATION,
                label="Equation working",
            ),
        ],
        equation_format="latex",
        allow_equation_rearrangement=allow_rearrangement,
        allow_equation_substitution=allow_substitution,
        allow_equation_simplification=allow_simplification,
        allow_equation_steps=allow_steps,
        allow_undo=True,
        allow_clear=True,
    )


def mixed_graph_equation_palette() -> AssessmentQuestionInteractionConfig:
    """
    Mixed graph/equation palette for questions requiring both visual and
    mathematical working.
    """

    graph = graphing_palette()

    return AssessmentQuestionInteractionConfig(
        version=1,
        mode="mixed",
        palette_id="general.graph_equation",
        palette_label="Graph and equation tools",
        coordinate_system="graph",
        snap_to_grid=True,
        tools=[
            *graph.tools,
            _tool(
                tool_id="equation_editor",
                tool_type=AssessmentInteractionToolType.EQUATION_EDITOR,
                label="Equation editor",
            ),
            _tool(
                tool_id="equation_manipulation",
                tool_type=AssessmentInteractionToolType.EQUATION_MANIPULATION,
                label="Equation working",
            ),
        ],
        equation_format="latex",
        allow_equation_rearrangement=True,
        allow_equation_substitution=True,
        allow_equation_simplification=True,
        allow_equation_steps=True,
        allow_undo=True,
        allow_clear=True,
    )


PALETTE_BUILDERS: dict[
    str,
    Callable[[], AssessmentQuestionInteractionConfig],
] = {
    "chemistry.atomic_structure": chemistry_atomic_structure_palette,
    "physics.fields_vectors": physics_field_palette,
    "general.graphing": graphing_palette,
    "general.diagram_labelling": general_diagram_labelling_palette,
    "general.equation_editor": equation_editor_palette,
    "general.graph_equation": mixed_graph_equation_palette,
}


def get_palette(
    palette_id: str,
) -> AssessmentQuestionInteractionConfig:
    """
    Return one validated built-in palette by stable id.
    """

    try:
        builder = PALETTE_BUILDERS[palette_id]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported assessment interaction palette: {palette_id!r}.",
        ) from exc

    return builder()


def list_palette_ids() -> tuple[str, ...]:
    """
    Return stable built-in palette identifiers in deterministic order.
    """

    return tuple(
        sorted(
            PALETTE_BUILDERS,
        )
    )


def infer_interaction_config(
    *,
    question_text: str | None,
    question_type: AssessmentQuestionType | str,
) -> AssessmentQuestionInteractionConfig | None:
    """
    Conservatively propose an interaction palette from examination wording.

    This function deliberately proposes only high-confidence configurations.
    Teacher review remains authoritative and may replace or remove the proposed
    configuration before canonical import.
    """

    text = _normalise_text(
        question_text,
    )

    if not text:
        return None

    try:
        resolved_type = AssessmentQuestionType(
            question_type,
        )
    except ValueError:
        return None

    # Atomic-structure placement: require both atomic context and named particle
    # vocabulary. This intentionally still works when PDF text extraction loses
    # the actual ×/●/○ glyphs.
    atomic_context = any(
        phrase in text
        for phrase in (
            "atom",
            "atomic structure",
            "nucleus",
            "particles in an atom",
        )
    )
    atomic_particles = (
        "electron" in text
        and "proton" in text
        and "neutron" in text
    )

    if (
        resolved_type == AssessmentQuestionType.DIAGRAM_ANNOTATION
        and atomic_context
        and atomic_particles
    ):
        return chemistry_atomic_structure_palette()

    graph_terms = any(
        phrase in text
        for phrase in (
            "plot the graph",
            "plot a graph",
            "plot the points",
            "plot these points",
            "line of best fit",
            "draw a graph",
            "label the axes",
            "label the axis",
        )
    )

    equation_terms = any(
        phrase in text
        for phrase in (
            "rearrange the equation",
            "rearrange this equation",
            "write an equation",
            "write the equation",
            "use the equation",
            "use this equation",
            "use the formula",
            "using the formula",
            "substitute into",
            "simplify the expression",
            "show your algebra",
        )
    )

    if graph_terms and equation_terms:
        return mixed_graph_equation_palette()

    if graph_terms:
        return graphing_palette()

    if (
        equation_terms
        and resolved_type
        in {
            AssessmentQuestionType.WRITTEN,
            AssessmentQuestionType.NUMERIC,
        }
    ):
        return equation_editor_palette()

    if resolved_type == AssessmentQuestionType.DIAGRAM_ANNOTATION:
        if any(
            phrase in text
            for phrase in (
                "label the diagram",
                "label this diagram",
                "mark with a cross",
                "mark on the diagram",
                "draw an arrow",
                "complete the diagram",
            )
        ):
            return general_diagram_labelling_palette()

    return None


def interaction_config_as_dict(
    config: AssessmentQuestionInteractionConfig | None,
) -> dict[str, object] | None:
    """
    Convert a validated config into JSON-safe proposal/canonical storage data.
    """

    if config is None:
        return None

    return config.model_dump(
        mode="json",
        exclude_none=True,
    )
