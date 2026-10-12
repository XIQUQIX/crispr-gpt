"""CRISPR activation / interference pipeline.

Task names and dependencies follow the paper's task description table
(Appendix B). Note this modality ends in a qPCR primer-design task rather than
the Sanger/NGS pair used by the editing modalities. Every step is structural
only: no CRISPRa/i content ships in the lite release. Fill these in here --
see `pending.py`.
"""

from .pending import make_pending_state

StateStep1 = make_pending_state(
    task_id="act_rep.StateStep1",
    title="CRISPRa/i -- activation or repression system selection",
    paper_ref="Table 1, 'CRISPR/Cas Activation/Interference system selection'",
    requires=[
        "expert-authored comparison of activation and repression effectors with citations",
        "guidance on promoter-proximal targeting windows",
    ],
)

StateStep2 = make_pending_state(
    task_id="act_rep.StateStep2",
    title="CRISPRa/i -- delivery approach selection",
    paper_ref="Table 1, 'Delivery method selection'",
    requires=[
        "expert-authored delivery options with cell-type guidance and citations",
        "web-search tool integration for context-specific recommendations",
    ],
)

StateStep3 = make_pending_state(
    task_id="act_rep.StateStep3",
    title="CRISPRa/i -- guideRNA design",
    paper_ref="Table 1, 'sgRNA design for activation/interference'",
    requires=[
        "CRISPRa/i sgRNA library covering transcription start sites",
        "TSS annotation source",
    ],
)

StateStep4 = make_pending_state(
    task_id="act_rep.StateStep4",
    title="CRISPRa/i -- experimental protocol recommendation",
    paper_ref="Table 1, 'experimental protocol recommendation'",
    requires=[
        "expert-authored protocols conditioned on effector and delivery route",
        "protocol retrieval over the curated document set",
    ],
)

StateStep4_5_1 = make_pending_state(
    task_id="act_rep.StateStep4_5_1",
    title="CRISPRa/i -- validation and primer design (qPCR)",
    paper_ref="Table 1, 'validation protocol recommendation and primer design for qPCR'",
    requires=[
        "expert-authored qPCR validation protocol including reference-gene choice",
        "Primer3 integration for primer design",
    ],
)
