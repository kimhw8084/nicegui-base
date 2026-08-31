"""Wave 69 external promotion execution-adapter qualification example.

No approved company execution adapter is available in this generic source environment,
so an artifact-backed adapter qualification that omits observed release identity remains PENDING.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from nicegui_base import (
    PromotionExecutionAdapterQualificationStatus,
    PromotionRehearsalKind,
    build_promotion_execution_adapter_qualification,
    capture_target_evidence_artifact,
    verify_promotion_execution_adapter_qualification,
)


def main() -> None:
    with TemporaryDirectory() as directory:
        artifact_path = Path(directory) / 'external-qualification.json'
        artifact_path.write_text('{"status":"qualified"}\n', encoding='utf-8')
        qualification = build_promotion_execution_adapter_qualification(
            'example-company-release-adapter',
            '1.0.0',
            requested_status='qualified',
            supported_operations=tuple(PromotionRehearsalKind),
            artifacts=(capture_target_evidence_artifact(artifact_path, key='qualification-run'),),
            # Deliberately omit observed framework/NiceGUI identity in this source-only example.
        )
        verification = verify_promotion_execution_adapter_qualification(qualification)
        assert verification.status is PromotionExecutionAdapterQualificationStatus.PENDING
        print(f'adapter={qualification.adapter_key} status={verification.status.value}')


if __name__ == '__main__':
    main()
