"""Prime-editing pipeline.

Task names and dependencies follow the paper's task description table
(Appendix B). Every step is structural only: no prime-editing content ships in
the lite release. Fill these in here -- see `pending.py`.
"""

from .pending import make_pending_state
from .routing import make_readout_router

StateStep1 = make_pending_state(
    task_id="prime_editing.StateStep1",
    title="Prime editing -- prime editing system selection",
    paper_ref="Table 1, 'Prime editing system selection'",
    requires=[
        "expert-authored comparison of prime editor versions with citations",
        "guidance on nicking strategy",
    ],
)

StateStep2 = make_pending_state(
    task_id="prime_editing.StateStep2",
    title="Prime editing -- delivery approach selection",
    paper_ref="Table 1, 'Delivery method selection'",
    requires=[
        "expert-authored delivery options with cell-type guidance and citations",
        "web-search tool integration for context-specific recommendations",
    ],
)

StateStep3 = make_pending_state(
    task_id="prime_editing.StateStep3",
    title="Prime editing -- pegRNA design",
    paper_ref="Table 1, 'pegRNA design for prime editing'",
    requires=[
        "pegRNA design tool integration (PBS / RT template / nicking guide)",
        "handling of the intended edit specification",
    ],
)

StateStep4 = make_pending_state(
    task_id="prime_editing.StateStep4",
    title="Prime editing -- experimental protocol recommendation",
    paper_ref="Table 1, 'experimental protocol recommendation'",
    requires=[
        "expert-authored protocols conditioned on editor and delivery route",
        "protocol retrieval over the curated document set",
    ],
)

StateStep4_5_1_Sanger = make_pending_state(
    task_id="prime_editing.StateStep4_5_1_Sanger",
    title="Prime editing -- validation and primer design (Sanger)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for Sanger readout",
        "Primer3 integration for primer design",
    ],
)

StateStep4_5_1_NGS = make_pending_state(
    task_id="prime_editing.StateStep4_5_1_NGS",
    title="Prime editing -- validation and primer design (NGS)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design'",
    requires=[
        "expert-authored validation protocol for NGS readout",
        "Primer3 integration for primer design",
    ],
)

StateStep4_5 = make_readout_router(
    task_id="prime_editing.StateStep4_5",
    heading="Validating the editing outcome",
    sanger_state=StateStep4_5_1_Sanger,
    ngs_state=StateStep4_5_1_NGS,
)
