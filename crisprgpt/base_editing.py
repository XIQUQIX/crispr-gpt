"""Base-editing pipeline.

Task names and dependencies follow the paper's task description table
(Appendix B). Every step is structural only: no base-editing content ships in
the lite release. Fill these in here -- see `pending.py`.
"""

from .pending import make_pending_state
from .routing import make_readout_router

StateStep1 = make_pending_state(
    task_id="base_editing.StateStep1",
    title="Base editing -- base editor system selection",
    paper_ref="Table 1, 'Base editing system selection'",
    requires=[
        "expert-authored comparison of cytosine/adenine/dual base editors with citations",
        "editing-window and bystander guidance",
    ],
)

StateStep2 = make_pending_state(
    task_id="base_editing.StateStep2",
    title="Base editing -- guideRNA design",
    paper_ref="Table 1, 'sgRNA design for base editing'",
    requires=[
        "base-editing sgRNA library or design tool integration",
        "target-base positioning within the editing window",
    ],
)

StateStep3 = make_pending_state(
    task_id="base_editing.StateStep3",
    title="Base editing -- delivery approach selection",
    paper_ref="Table 1, 'Delivery method selection'",
    requires=[
        "expert-authored delivery options with cell-type guidance and citations",
        "web-search tool integration for context-specific recommendations",
    ],
)

StateStep4 = make_pending_state(
    task_id="base_editing.StateStep4",
    title="Base editing -- experimental protocol recommendation",
    paper_ref="Table 1, 'experimental protocol recommendation'",
    requires=[
        "expert-authored protocols conditioned on editor and delivery route",
        "protocol retrieval over the curated document set",
    ],
)

StateStep4_5_1_Sanger = make_pending_state(
    task_id="base_editing.StateStep4_5_1_Sanger",
    title="Base editing -- validation and primer design (Sanger)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for Sanger readout",
        "Primer3 integration for primer design",
    ],
)

StateStep4_5_1_NGS = make_pending_state(
    task_id="base_editing.StateStep4_5_1_NGS",
    title="Base editing -- validation and primer design (NGS)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for NGS readout",
        "Primer3 integration for primer design",
    ],
)

StateStep4_5 = make_readout_router(
    task_id="base_editing.StateStep4_5",
    heading="Validating the editing outcome",
    sanger_state=StateStep4_5_1_Sanger,
    ngs_state=StateStep4_5_1_NGS,
)
