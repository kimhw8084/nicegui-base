from __future__ import annotations

import inspect
from typing import Any, Callable

from nicegui_base.analysis import AnalysisContext, AnalyticalPanelController, SelectionBus
from nicegui_base.components import StatusIntent
from nicegui_base.integrations.nicegui_analysis import AnalyticalPanel
from nicegui_base.integrations.nicegui_components import Panel, Select, StatusBadge
from nicegui_base.integrations.nicegui_content import MetricCard, MetricStrip, ProgressMetric
from nicegui_base.certification.semiconductor_orchestrator import PromotionDecisionStatus, SemiconductorPromotionDecision
from nicegui_base.certification.semiconductor_promotion import PromotionCandidateStatus, StablePromotionCandidate
from nicegui_base.certification.semiconductor_execution import (
    PromotionHandoffStatus, StablePromotionOperationalHandoff, TargetExecutionIntake,
    TargetExecutionIntakeStatus, TargetExecutionIntakeVerification,
)
from nicegui_base.certification.semiconductor_release_audit import (
    PromotionExecutionAdapterQualification, PromotionExecutionAdapterQualificationStatus,
    PromotionExecutionAdapterQualificationVerification, ReleaseAuditClosure, ReleaseAuditStatus,
)
from nicegui_base.certification.semiconductor_release_acceptance import (
    StablePromotionClosureStatus, StableReleaseEvidenceAcceptance, StableReleaseEvidenceAcceptanceStatus,
    StableReleaseEvidenceAcceptanceVerification, StableReleasePromotionClosure,
)
from nicegui_base.certification.semiconductor_publication import (
    PostPromotionVerificationStatus, StablePostPromotionVerification, StableReleasePublicationEvidence,
    StableReleasePublicationStatus, StableReleasePublicationVerification,
)
from nicegui_base.certification.semiconductor_stability import (
    PostReleaseStabilityEvidence, PostReleaseStabilityStatus, PostReleaseStabilityVerification,
    RollbackReadinessStatus, StableRollbackReadinessVerification,
)
from nicegui_base.certification.semiconductor_operations import (
    IncidentRollbackAuditClosure, IncidentRollbackAuditStatus, SustainedOperationsAcceptanceStatus,
    SustainedOperationsAcceptanceVerification, SustainedOperationsEvidenceAcceptance,
)
from nicegui_base.certification.semiconductor_continuity import (
    OperationalAssuranceContinuityDossier, OperationalAssuranceContinuityStatus,
    SustainedOperationsEvidenceRenewal, SustainedOperationsRenewalStatus, SustainedOperationsRenewalVerification,
)
from nicegui_base.certification.semiconductor_longitudinal import (
    LongitudinalOperationalAssuranceDossier, OperationalAssuranceLedgerStatus, OperationalAssuranceRenewalLedger,
)
from nicegui_base.certification.semiconductor_longitudinal_review import (
    EvidenceExceptionGovernanceDossier, EvidenceExceptionGovernanceStatus, LongitudinalAssuranceReviewRecord, LongitudinalAssuranceReviewStatus,
)
from nicegui_base.semiconductor import (
    OnboardingFieldState, OperationalReadinessState, RecipeOnboardingView, RecipeSetupWorkflow, RuntimeExperienceState, RuntimeExperienceStatus, SemiconductorOperationalReadiness,
    SemiconductorAnalyticalSurface, SetupStepStatus, get_semiconductor_surface,
)


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render NiceGUI Base semiconductor components') from exc
    return ui


async def _invoke(callback: Callable[..., Any] | None, *args) -> Any:
    if callback is None:
        return None
    result = callback(*args)
    if inspect.isawaitable(result):
        return await result
    return result


class SemiconductorAnalyticalPanel(AnalyticalPanel):
    """NiceGUI shell binding every semiconductor domain surface to the shared analytical contract."""
    def __init__(self,surface_key:str,context:AnalysisContext,selections:SelectionBus, *, title:str|None=None,description:str|None=None,controller:AnalyticalPanelController|None=None,**kwargs):
        definition=get_semiconductor_surface(surface_key); controller=controller or AnalyticalPanelController(); self.surface=SemiconductorAnalyticalSurface(surface_key,context,selections,controller=controller)
        super().__init__(title or definition.purpose,controller=controller,description=description,**kwargs)
    def close(self):
        self.surface.close()
        super().close()


class SemiconductorOnboardingPanel:
    """First-class setup surface for explainable Wave 63/64 recipe binding decisions."""
    def __init__(self, view: RecipeOnboardingView, *, on_bind: Callable[[str, str], Any] | None = None):
        self.view = view
        self.on_bind = on_bind
        ui = _ui()
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Data onboarding').classes('cui-analytical-panel__title')
                    ui.label(f'{view.source_key} → {view.recipe_key}').classes('cui-caption')
                StatusBadge('Ready' if view.ready else 'Setup required', intent=StatusIntent.SUCCESS if view.ready else StatusIntent.WARNING)
            ProgressMetric('Semantic bindings', view.completion_ratio, display_value=f'{view.bound_fields}/{len(view.fields)}', description='Only high-confidence or explicit mappings are treated as bound.')
            for field in view.fields:
                with ui.element('section').classes('cui-property-grid').props(f'data-field-state="{field.state.value}"'):
                    with ui.element('div').classes('cui-property'):
                        ui.label(field.logical_field).classes('cui-kv-label')
                        ui.label(field.description or ('Required semantic' if field.required else 'Optional semantic')).classes('cui-caption')
                    intent = {
                        OnboardingFieldState.BOUND: StatusIntent.SUCCESS,
                        OnboardingFieldState.AMBIGUOUS: StatusIntent.WARNING,
                        OnboardingFieldState.REQUIRED: StatusIntent.DANGER,
                        OnboardingFieldState.OPTIONAL: StatusIntent.NEUTRAL,
                    }[field.state]
                    StatusBadge(field.state.value.replace('_',' ').title(), intent=intent)
                    if field.source_field is not None:
                        ui.label(field.source_field).classes('cui-kv-value')
                    elif field.alternatives:
                        options = {item.source_field: f'{item.source_field} · {item.score:.0%}' for item in field.alternatives}
                        async def changed(event, logical=field.logical_field):
                            if getattr(event, 'value', None):
                                await _invoke(self.on_bind, logical, str(event.value))
                        Select(f'Map {field.logical_field}', options, description=field.reason, required=field.required, searchable=True, on_change=changed)
                    elif field.action:
                        ui.label(field.action).classes('cui-caption')
            if view.blocking_actions:
                ui.label('Required before production use').classes('cui-kv-label')
                for action in view.blocking_actions:
                    ui.label(f'• {action}').classes('cui-caption')


class SemiconductorSetupWizard:
    """Guided, read-only setup workflow shell; field changes remain explicit callbacks."""
    def __init__(self, workflow: RecipeSetupWorkflow, *, on_bind: Callable[[str, str], Any] | None = None):
        self.workflow = workflow
        self.on_bind = on_bind
        ui = _ui()
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Production setup').classes('cui-analytical-panel__title')
                    ui.label(f'{workflow.provider}:{workflow.source_key} → {workflow.recipe_key}').classes('cui-caption')
                StatusBadge('Release ready' if workflow.ready_for_release else ('Runnable' if workflow.ready_to_run else 'Setup required'), intent=StatusIntent.SUCCESS if workflow.ready_for_release else StatusIntent.WARNING)
            ProgressMetric('Setup completion', workflow.completion_ratio, display_value=f'{workflow.completion_ratio:.0%}', description='Release readiness stays pending until every target-environment gate has evidence.')
            for step in workflow.steps:
                intent = {
                    SetupStepStatus.COMPLETE: StatusIntent.SUCCESS,
                    SetupStepStatus.ACTION_REQUIRED: StatusIntent.WARNING,
                    SetupStepStatus.BLOCKED: StatusIntent.DANGER,
                    SetupStepStatus.PENDING: StatusIntent.INFO,
                    SetupStepStatus.SKIPPED: StatusIntent.NEUTRAL,
                }[step.status]
                with ui.element('section').classes('cui-property-grid').props(f'data-setup-step="{step.key}" data-setup-status="{step.status.value}"'):
                    with ui.element('div').classes('cui-property'):
                        ui.label(step.title).classes('cui-kv-label')
                        ui.label(step.summary).classes('cui-caption')
                    StatusBadge(step.status.value.replace('_',' ').title(), intent=intent)
                    for action in step.actions[:3]:
                        ui.label(f'• {action}').classes('cui-caption')
            if not workflow.onboarding.ready:
                SemiconductorOnboardingPanel(workflow.onboarding, on_bind=on_bind)


class SemiconductorRuntimeStatusPanel:
    """Compact runtime experience surface shared by all eight recipe applications."""
    def __init__(self, state: RuntimeExperienceState):
        self.state = state
        ui = _ui()
        intent = {
            RuntimeExperienceStatus.READY: StatusIntent.SUCCESS,
            RuntimeExperienceStatus.DEGRADED: StatusIntent.WARNING,
            RuntimeExperienceStatus.BLOCKED: StatusIntent.DANGER,
            RuntimeExperienceStatus.LOADING: StatusIntent.INFO,
            RuntimeExperienceStatus.EMPTY: StatusIntent.NEUTRAL,
            RuntimeExperienceStatus.STALE: StatusIntent.WARNING,
            RuntimeExperienceStatus.PARTIAL: StatusIntent.WARNING,
        }[state.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Runtime status').classes('cui-analytical-panel__title')
                    ui.label(state.message).classes('cui-caption')
                StatusBadge(state.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Provider', state.provider)
                MetricCard('Selections', state.selection_count)
                MetricCard('Context filters', len(state.manufacturing_context))
                MetricCard('Panels', len(state.panel_states))
            if state.next_actions:
                ui.label('Next actions').classes('cui-kv-label')
                for action in state.next_actions:
                    ui.label(f'• {action}').classes('cui-caption')


__all__=['SemiconductorAnalyticalPanel','SemiconductorDeploymentReadinessPanel','SemiconductorOnboardingPanel','SemiconductorPromotionCandidatePanel','SemiconductorPromotionOperationalHandoffPanel','SemiconductorRuntimeStatusPanel','SemiconductorSetupWizard','SemiconductorTargetExecutionIntakePanel']


class SemiconductorDeploymentReadinessPanel:
    """Compact operational + stable-promotion surface; never converts pending evidence into PASS."""
    def __init__(self, readiness: SemiconductorOperationalReadiness, decision: SemiconductorPromotionDecision | None = None):
        self.readiness = readiness
        self.decision = decision
        ui = _ui()
        readiness_intent = {
            OperationalReadinessState.READY: StatusIntent.SUCCESS,
            OperationalReadinessState.DEGRADED: StatusIntent.WARNING,
            OperationalReadinessState.BLOCKED: StatusIntent.DANGER,
            OperationalReadinessState.PENDING: StatusIntent.INFO,
        }[readiness.state]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Deployment readiness').classes('cui-analytical-panel__title')
                    ui.label(f'{readiness.provider}:{readiness.source_key} → {readiness.recipe_key}').classes('cui-caption')
                StatusBadge(readiness.state.value.title(), intent=readiness_intent)
            with MetricStrip():
                MetricCard('Runnable', 'Yes' if readiness.ready_to_run else 'No')
                MetricCard('Operational release', 'Ready' if readiness.ready_for_release else 'Pending')
                MetricCard('Checks', len(readiness.checks))
                MetricCard('Promotion', 'Not evaluated' if decision is None else decision.status.value.title())
            if decision is not None:
                promotion_intent = {
                    PromotionDecisionStatus.PROMOTABLE: StatusIntent.SUCCESS,
                    PromotionDecisionStatus.PENDING: StatusIntent.WARNING,
                    PromotionDecisionStatus.BLOCKED: StatusIntent.DANGER,
                }[decision.status]
                StatusBadge(f'Stable promotion: {decision.status.value}', intent=promotion_intent)
            actions = readiness.next_actions if decision is None else tuple(dict.fromkeys((*readiness.next_actions, *decision.next_actions)))
            if actions:
                ui.label('Next actions').classes('cui-kv-label')
                for action in actions[:8]:
                    ui.label(f'• {action}').classes('cui-caption')


class SemiconductorPromotionCandidatePanel:
    """Actionable stable-channel candidate diagnostics; never upgrades evidence or rehearsal status."""
    def __init__(self, candidate: StablePromotionCandidate):
        self.candidate = candidate
        ui = _ui()
        intent = {
            PromotionCandidateStatus.READY: StatusIntent.SUCCESS,
            PromotionCandidateStatus.PENDING: StatusIntent.WARNING,
            PromotionCandidateStatus.BLOCKED: StatusIntent.DANGER,
        }[candidate.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable promotion candidate').classes('cui-analytical-panel__title')
                    ui.label(f'{candidate.channel} → {candidate.target_version} · {candidate.candidate_id[:12]}').classes('cui-caption')
                StatusBadge(candidate.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Evidence', candidate.evidence.decision.status.value.title())
                MetricCard('Recipes', len(candidate.evidence.recipe_keys))
                MetricCard('Rehearsals', len(candidate.rehearsals))
                MetricCard('Gaps', len(candidate.gaps))
            if candidate.gaps:
                ui.label('Promotion gaps').classes('cui-kv-label')
                for gap in candidate.gaps[:10]:
                    ui.label(f'• {gap.message}').classes('cui-caption')
            if candidate.next_actions:
                ui.label('Next actions').classes('cui-kv-label')
                for action in candidate.next_actions[:8]:
                    ui.label(f'• {action}').classes('cui-caption')

class SemiconductorTargetExecutionIntakePanel:
    """Target-execution intake diagnostics; requested PASS is never displayed as verified without the intake verification contract."""
    def __init__(self, intake: TargetExecutionIntake, verification: TargetExecutionIntakeVerification):
        self.intake = intake
        self.verification = verification
        ui = _ui()
        intent = {
            TargetExecutionIntakeStatus.VERIFIED: StatusIntent.SUCCESS,
            TargetExecutionIntakeStatus.PENDING: StatusIntent.WARNING,
            TargetExecutionIntakeStatus.BLOCKED: StatusIntent.DANGER,
        }[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Target execution intake').classes('cui-analytical-panel__title')
                    ui.label(f'{intake.provider}:{intake.source_key} → {intake.recipe_key} · {intake.intake_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Observations', len(intake.observations))
                MetricCard('Artifacts', len(intake.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('NiceGUI', intake.environment.nicegui_version or 'Unobserved')
            if verification.findings:
                ui.label('Intake diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]:
                    ui.label(f'• {finding.message}').classes('cui-caption')


class SemiconductorPromotionOperationalHandoffPanel:
    """Verified candidate-package handoff surface; never performs deployment or mutates promotion truth."""
    def __init__(self, handoff: StablePromotionOperationalHandoff):
        self.handoff = handoff
        ui = _ui()
        intent = {
            PromotionHandoffStatus.READY: StatusIntent.SUCCESS,
            PromotionHandoffStatus.PENDING: StatusIntent.WARNING,
            PromotionHandoffStatus.BLOCKED: StatusIntent.DANGER,
        }[handoff.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable promotion operational handoff').classes('cui-analytical-panel__title')
                    ui.label(f'{handoff.candidate.channel} → {handoff.candidate.target_version} · {handoff.handoff_id[:12]}').classes('cui-caption')
                StatusBadge(handoff.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Candidate', handoff.candidate.status.value.title())
                MetricCard('Archive', 'Verified' if handoff.candidate_archive.verified else 'Blocked')
                MetricCard('Recipes', len(handoff.candidate.evidence.recipe_keys))
                MetricCard('Deploy action', 'Not performed')
            if handoff.next_actions:
                ui.label('Next actions').classes('cui-kv-label')
                for action in handoff.next_actions[:8]:
                    ui.label(f'• {action}').classes('cui-caption')

class SemiconductorPromotionExecutionAdapterQualificationPanel:
    """Artifact-backed external execution-adapter qualification diagnostics; never interprets a ticket/reference as approval."""
    def __init__(self, qualification: PromotionExecutionAdapterQualification, verification: PromotionExecutionAdapterQualificationVerification):
        self.qualification = qualification
        self.verification = verification
        ui = _ui()
        intent = {
            PromotionExecutionAdapterQualificationStatus.QUALIFIED: StatusIntent.SUCCESS,
            PromotionExecutionAdapterQualificationStatus.PENDING: StatusIntent.WARNING,
            PromotionExecutionAdapterQualificationStatus.BLOCKED: StatusIntent.DANGER,
        }[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Promotion execution adapter qualification').classes('cui-analytical-panel__title')
                    ui.label(f'{qualification.adapter_key}@{qualification.adapter_version} · {qualification.qualification_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Capabilities', len(qualification.supported_operations))
                MetricCard('Artifacts', len(qualification.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Approval ref', qualification.approval_reference or 'Not supplied')
            if verification.findings:
                ui.label('Qualification diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]:
                    ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('Approval references are metadata only; qualification requires current artifact-backed evidence.').classes('cui-caption')


class SemiconductorReleaseAuditClosurePanel:
    """Final release-channel audit diagnostics; CLOSED never changes candidate/target-gate truth or implies framework deployment."""
    def __init__(self, audit: ReleaseAuditClosure):
        self.audit = audit
        ui = _ui()
        intent = {
            ReleaseAuditStatus.CLOSED: StatusIntent.SUCCESS,
            ReleaseAuditStatus.PENDING: StatusIntent.WARNING,
            ReleaseAuditStatus.BLOCKED: StatusIntent.DANGER,
        }[audit.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable release audit closure').classes('cui-analytical-panel__title')
                    ui.label(f'{audit.handoff.candidate.channel} → {audit.handoff.candidate.target_version} · {audit.audit_id[:12]}').classes('cui-caption')
                StatusBadge(audit.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Handoff', audit.handoff.status.value.title())
                MetricCard('Adapter', audit.execution_adapter_qualification.adapter_key)
                MetricCard('Operations', len(audit.operation_records))
                MetricCard('Findings', len(audit.findings))
            if audit.findings:
                ui.label('Audit diagnostics').classes('cui-kv-label')
                for finding in audit.findings[:10]:
                    ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('Audit evidence is complete. Candidate and target-gate status remain unchanged.').classes('cui-caption')



class SemiconductorStableReleaseEvidenceAcceptancePanel:
    """External stable-release evidence acceptance diagnostics; external authority/reference metadata is never interpreted as approval by itself."""
    def __init__(self, acceptance: StableReleaseEvidenceAcceptance, verification: StableReleaseEvidenceAcceptanceVerification):
        self.acceptance = acceptance
        self.verification = verification
        ui = _ui()
        intent = {
            StableReleaseEvidenceAcceptanceStatus.ACCEPTED: StatusIntent.SUCCESS,
            StableReleaseEvidenceAcceptanceStatus.PENDING: StatusIntent.WARNING,
            StableReleaseEvidenceAcceptanceStatus.BLOCKED: StatusIntent.DANGER,
        }[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable release evidence acceptance').classes('cui-analytical-panel__title')
                    ui.label(f'{acceptance.candidate_id[:12]} · {acceptance.acceptance_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Requested', acceptance.requested_status.value.title())
                MetricCard('Artifacts', len(acceptance.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Approval ref', acceptance.approval_reference or 'Not supplied')
            if verification.findings:
                ui.label('Acceptance diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]:
                    ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('Acceptance is hash-bound evidence; it does not rewrite canonical target gates or promotion truth.').classes('cui-caption')


class SemiconductorStableReleasePublicationPanel:
    """External publication evidence diagnostics; no deployment/publication action is executed by the framework."""
    def __init__(self, evidence: StableReleasePublicationEvidence, verification: StableReleasePublicationVerification):
        self.evidence = evidence; self.verification = verification; ui = _ui()
        intent = {StableReleasePublicationStatus.PUBLISHED: StatusIntent.SUCCESS, StableReleasePublicationStatus.PENDING: StatusIntent.WARNING, StableReleasePublicationStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable release publication evidence').classes('cui-analytical-panel__title')
                    ui.label(f'{evidence.target_version} · {evidence.publication_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Requested', evidence.requested_status.value.title())
                MetricCard('Artifacts', len(evidence.artifacts))
                MetricCard('Publication ref', evidence.publication_reference or 'Not supplied')
                MetricCard('Framework action', 'None')
            if verification.findings:
                ui.label('Publication diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('PUBLISHED is accepted only from immutable external evidence bound to the exact Wave 70 closure; it never means NiceGUI Base performed publication.').classes('cui-caption')


class SemiconductorPostPromotionVerificationPanel:
    """Post-release dossier diagnostics; VERIFIED records external evidence and never implies continuous monitoring."""
    def __init__(self, verification: StablePostPromotionVerification):
        self.verification = verification; ui = _ui()
        intent = {PostPromotionVerificationStatus.VERIFIED: StatusIntent.SUCCESS, PostPromotionVerificationStatus.PENDING: StatusIntent.WARNING, PostPromotionVerificationStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Post-promotion verification').classes('cui-analytical-panel__title')
                    ui.label(f'{verification.policy.target_version} · {verification.verification_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Publication', verification.publication.requested_status.value.title())
                MetricCard('Evidence', len(verification.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Monitoring', 'External')
            if verification.findings:
                ui.label('Post-release diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('The immutable publication/post-release evidence dossier verifies. Ongoing production monitoring remains external.').classes('cui-caption')


class SemiconductorPostReleaseStabilityPanel:
    """Production-health/incident evidence diagnostics; NiceGUI Base verifies evidence but performs no monitoring or incident response."""
    def __init__(self, evidence: PostReleaseStabilityEvidence, verification: PostReleaseStabilityVerification):
        self.evidence = evidence; self.verification = verification; ui = _ui()
        intent = {PostReleaseStabilityStatus.STABLE: StatusIntent.SUCCESS, PostReleaseStabilityStatus.PENDING: StatusIntent.WARNING, PostReleaseStabilityStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Post-release stability evidence').classes('cui-analytical-panel__title')
                    ui.label(f'{evidence.target_version} · {evidence.stability_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Requested', evidence.requested_status.value.title())
                MetricCard('Evidence', len(evidence.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Monitoring', 'External')
            if verification.findings:
                ui.label('Stability diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('STABLE records hash-bound external production-health/incident evidence only; no monitoring or incident response is performed by NiceGUI Base.').classes('cui-caption')


class SemiconductorRollbackReadinessPanel:
    """Rollback-readiness diagnostics; READY never means NiceGUI Base executed or authorized a rollback."""
    def __init__(self, verification: StableRollbackReadinessVerification):
        self.verification = verification; ui = _ui()
        intent = {RollbackReadinessStatus.READY: StatusIntent.SUCCESS, RollbackReadinessStatus.PENDING: StatusIntent.WARNING, RollbackReadinessStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Rollback readiness verification').classes('cui-analytical-panel__title')
                    ui.label(f'{verification.policy.target_version} · {verification.readiness_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Stability', verification.stability_evidence.requested_status.value.title())
                MetricCard('Readiness evidence', len(verification.rollback_artifacts))
                MetricCard('Execution evidence', len(verification.rollback_execution_artifacts))
                MetricCard('Framework rollback', 'None')
            if verification.findings:
                ui.label('Rollback diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('Rollback readiness evidence verifies. Any actual rollback remains an external operational action.').classes('cui-caption')


class SemiconductorSustainedOperationsAcceptancePanel:
    """Sustained-operations acceptance diagnostics; accepted evidence remains external and does not perform monitoring."""
    def __init__(self, acceptance: SustainedOperationsEvidenceAcceptance, verification: SustainedOperationsAcceptanceVerification):
        self.acceptance = acceptance; self.verification = verification; ui = _ui()
        intent = {SustainedOperationsAcceptanceStatus.ACCEPTED: StatusIntent.SUCCESS, SustainedOperationsAcceptanceStatus.PENDING: StatusIntent.WARNING, SustainedOperationsAcceptanceStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Sustained operations evidence acceptance').classes('cui-analytical-panel__title')
                    ui.label(f'{acceptance.target_version} · {acceptance.acceptance_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Requested', acceptance.requested_status.value.title())
                MetricCard('Evidence', len(acceptance.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Monitoring', 'External')
            if verification.findings:
                ui.label('Sustained-operations diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('ACCEPTED records hash-bound external sustained-operations evidence only; NiceGUI Base performs no monitoring, incident response, rollback, deployment or publication.').classes('cui-caption')


class SemiconductorIncidentRollbackAuditClosurePanel:
    """Incident/rollback audit diagnostics; CLOSED is documentary evidence closure, not operational execution."""
    def __init__(self, closure: IncidentRollbackAuditClosure):
        self.closure = closure; ui = _ui()
        intent = {IncidentRollbackAuditStatus.CLOSED: StatusIntent.SUCCESS, IncidentRollbackAuditStatus.PENDING: StatusIntent.WARNING, IncidentRollbackAuditStatus.BLOCKED: StatusIntent.DANGER}[closure.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Incident / rollback audit closure').classes('cui-analytical-panel__title')
                    ui.label(f'{closure.policy.target_version} · {closure.audit_id[:12]}').classes('cui-caption')
                StatusBadge(closure.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Sustained ops', closure.sustained_operations_acceptance.requested_status.value.title())
                MetricCard('Audit evidence', len(closure.audit_artifacts))
                MetricCard('Findings', len(closure.findings))
                MetricCard('Framework action', 'None')
            if closure.findings:
                ui.label('Audit diagnostics').classes('cui-kv-label')
                for finding in closure.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('The evidence audit is closed. Monitoring, incident response and rollback remain external company operations.').classes('cui-caption')


class SemiconductorSustainedOperationsRenewalPanel:
    """Wave 74 renewal diagnostics; renewal verifies external evidence freshness and never mutates historical Wave 73 truth."""
    def __init__(self, renewal: SustainedOperationsEvidenceRenewal, verification: SustainedOperationsRenewalVerification):
        self.renewal = renewal; self.verification = verification; ui = _ui()
        intent = {SustainedOperationsRenewalStatus.RENEWED: StatusIntent.SUCCESS, SustainedOperationsRenewalStatus.PENDING: StatusIntent.WARNING, SustainedOperationsRenewalStatus.BLOCKED: StatusIntent.DANGER}[verification.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Sustained operations evidence renewal').classes('cui-analytical-panel__title')
                    ui.label(f'{renewal.target_version} · {renewal.renewal_id[:12]}').classes('cui-caption')
                StatusBadge(verification.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Freshness', verification.freshness.status.value.title())
                MetricCard('Evidence', len(renewal.artifacts))
                MetricCard('Findings', len(verification.findings))
                MetricCard('Framework action', 'None')
            if verification.findings:
                ui.label('Renewal diagnostics').classes('cui-kv-label')
                for finding in verification.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('RENEWED records current hash-bound external evidence only; historical Wave 73 acceptance/audit truth remains immutable.').classes('cui-caption')


class SemiconductorOperationalAssuranceContinuityPanel:
    """Wave 74 continuity diagnostics; ASSURED/EXPIRING are documentary evidence states, not continuous monitoring."""
    def __init__(self, dossier: OperationalAssuranceContinuityDossier):
        self.dossier = dossier; ui = _ui()
        intent = {
            OperationalAssuranceContinuityStatus.ASSURED: StatusIntent.SUCCESS,
            OperationalAssuranceContinuityStatus.EXPIRING: StatusIntent.WARNING,
            OperationalAssuranceContinuityStatus.PENDING: StatusIntent.WARNING,
            OperationalAssuranceContinuityStatus.BLOCKED: StatusIntent.DANGER,
        }[dossier.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Operational assurance continuity').classes('cui-analytical-panel__title')
                    ui.label(f'{dossier.policy.target_version} · {dossier.continuity_id[:12]}').classes('cui-caption')
                StatusBadge(dossier.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Renewal', dossier.renewal_verification.status.value.title())
                MetricCard('Freshness', dossier.renewal_verification.freshness.status.value.title())
                MetricCard('Findings', len(dossier.findings))
                MetricCard('Monitoring', 'External')
            if dossier.findings:
                ui.label('Continuity diagnostics').classes('cui-kv-label')
                for finding in dossier.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('Current renewal evidence assures documentary continuity. NiceGUI Base performs no continuous monitoring or operational action.').classes('cui-caption')


class SemiconductorOperationalAssuranceRenewalLedgerPanel:
    """Wave 75 longitudinal renewal history; the ledger verifies external packages and performs no monitoring."""
    def __init__(self, ledger: OperationalAssuranceRenewalLedger):
        self.ledger = ledger; ui = _ui()
        intent = {
            OperationalAssuranceLedgerStatus.ASSURED: StatusIntent.SUCCESS,
            OperationalAssuranceLedgerStatus.EXPIRING: StatusIntent.WARNING,
            OperationalAssuranceLedgerStatus.PENDING: StatusIntent.WARNING,
            OperationalAssuranceLedgerStatus.BLOCKED: StatusIntent.DANGER,
        }[ledger.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Operational assurance renewal ledger').classes('cui-analytical-panel__title')
                    ui.label(f'{ledger.policy.target_version} · {ledger.ledger_id[:12]}').classes('cui-caption')
                StatusBadge(ledger.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Periods', len(ledger.entries))
                MetricCard('Findings', len(ledger.findings))
                MetricCard('Assessed', ledger.assessed_at[:10])
                MetricCard('Monitoring', 'External')
            if ledger.findings:
                ui.label('Longitudinal diagnostics').classes('cui-kv-label')
                for finding in ledger.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('The verified renewal chain has no current longitudinal gaps. NiceGUI Base performs no operational monitoring.').classes('cui-caption')


class SemiconductorLongitudinalAssuranceDossierPanel:
    """Wave 75 dossier view; ASSURED/EXPIRING remain documentary evidence states only."""
    def __init__(self, dossier: LongitudinalOperationalAssuranceDossier):
        self.dossier = dossier; ui = _ui()
        intent = {
            OperationalAssuranceLedgerStatus.ASSURED: StatusIntent.SUCCESS,
            OperationalAssuranceLedgerStatus.EXPIRING: StatusIntent.WARNING,
            OperationalAssuranceLedgerStatus.PENDING: StatusIntent.WARNING,
            OperationalAssuranceLedgerStatus.BLOCKED: StatusIntent.DANGER,
        }[dossier.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Longitudinal operational assurance').classes('cui-analytical-panel__title')
                    ui.label(f'{dossier.ledger.policy.target_version} · {dossier.dossier_id[:12]}').classes('cui-caption')
                StatusBadge(dossier.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Periods', len(dossier.ledger.entries))
                MetricCard('Ledger', dossier.ledger.ledger_id[:12])
                MetricCard('Findings', len(dossier.ledger.findings))
                MetricCard('Framework action', 'None')
            for finding in dossier.ledger.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('Longitudinal assurance is a hash-bound evidence review only; monitoring, incident response, rollback, deployment and publication remain external.').classes('cui-caption')


class SemiconductorLongitudinalAssuranceReviewPanel:
    """Wave 76 external review view; REVIEWED is documentary and does not rewrite Wave 75 evidence truth."""
    def __init__(self, review: LongitudinalAssuranceReviewRecord):
        self.review = review; ui = _ui()
        intent = {
            LongitudinalAssuranceReviewStatus.REVIEWED: StatusIntent.SUCCESS,
            LongitudinalAssuranceReviewStatus.PENDING: StatusIntent.WARNING,
            LongitudinalAssuranceReviewStatus.BLOCKED: StatusIntent.DANGER,
        }[review.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Longitudinal assurance review').classes('cui-analytical-panel__title')
                    ui.label(f'{review.authority} · {review.review_id[:12]}').classes('cui-caption')
                StatusBadge(review.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Reviewer', review.reviewer)
                MetricCard('Evidence', review.dossier.status.value.title())
                MetricCard('Exceptions', len(review.exceptions))
                MetricCard('Framework action', 'None')
            for finding in review.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('Review authority and exceptions are external documentary evidence; Wave 75 evidence truth is unchanged.').classes('cui-caption')


class SemiconductorEvidenceExceptionGovernancePanel:
    """Wave 76 bounded exception governance; GOVERNED never means the underlying evidence became PASS."""
    def __init__(self, dossier: EvidenceExceptionGovernanceDossier):
        self.dossier = dossier; ui = _ui()
        intent = {
            EvidenceExceptionGovernanceStatus.GOVERNED: StatusIntent.SUCCESS,
            EvidenceExceptionGovernanceStatus.PENDING: StatusIntent.WARNING,
            EvidenceExceptionGovernanceStatus.BLOCKED: StatusIntent.DANGER,
        }[dossier.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Evidence exception governance').classes('cui-analytical-panel__title')
                    ui.label(f'{dossier.review.review_reference} · {dossier.governance_id[:12]}').classes('cui-caption')
                StatusBadge(dossier.status.value.title(), intent=intent)
            with MetricStrip():
                MetricCard('Underlying', dossier.review.dossier.status.value.title())
                MetricCard('Review', dossier.review.status.value.title())
                MetricCard('Exceptions', len(dossier.review.exceptions))
                MetricCard('Synthetic PASS', 'No')
            for finding in dossier.findings[:10]: ui.label(f'• {finding.message}').classes('cui-caption')
            ui.label('Accepted bounded exceptions close review obligations only; missing/contradictory evidence is never converted into synthetic PASS.').classes('cui-caption')


class SemiconductorStablePromotionClosurePanel:
    """Final evidence-closure diagnostics; CLOSED is documentary closure and never a framework deployment/publication action."""
    def __init__(self, closure: StableReleasePromotionClosure):
        self.closure = closure
        ui = _ui()
        intent = {
            StablePromotionClosureStatus.CLOSED: StatusIntent.SUCCESS,
            StablePromotionClosureStatus.PENDING: StatusIntent.WARNING,
            StablePromotionClosureStatus.BLOCKED: StatusIntent.DANGER,
        }[closure.status]
        with Panel() as panel:
            self.element = panel.element
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    ui.label('Stable promotion evidence closure').classes('cui-analytical-panel__title')
                    ui.label(f'{closure.policy.key} → {closure.policy.target_version} · {closure.closure_id[:12]}').classes('cui-caption')
                StatusBadge(closure.status.value.title(), intent=intent)
            candidate = closure.release_audit.handoff.candidate
            with MetricStrip():
                MetricCard('Candidate', candidate.status.value.title())
                MetricCard('Promotion truth', candidate.evidence.decision.status.value.title())
                MetricCard('Acceptance', closure.evidence_acceptance.requested_status.value.title())
                MetricCard('Publish action', 'Not performed')
            if closure.findings:
                ui.label('Closure diagnostics').classes('cui-kv-label')
                for finding in closure.findings[:10]:
                    ui.label(f'• {finding.message}').classes('cui-caption')
            else:
                ui.label('Evidence closure is complete. Deployment/publication remains outside the generic framework.').classes('cui-caption')

__all__=['SemiconductorAnalyticalPanel','SemiconductorDeploymentReadinessPanel','SemiconductorOnboardingPanel','SemiconductorPostPromotionVerificationPanel','SemiconductorPostReleaseStabilityPanel','SemiconductorPromotionCandidatePanel','SemiconductorPromotionExecutionAdapterQualificationPanel','SemiconductorPromotionOperationalHandoffPanel','SemiconductorReleaseAuditClosurePanel','SemiconductorRollbackReadinessPanel','SemiconductorRuntimeStatusPanel','SemiconductorSetupWizard','SemiconductorStablePromotionClosurePanel','SemiconductorStableReleaseEvidenceAcceptancePanel','SemiconductorStableReleasePublicationPanel','SemiconductorTargetExecutionIntakePanel']
