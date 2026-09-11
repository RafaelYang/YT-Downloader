"""Keep installer publication independent of Actions artifact storage."""

from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/build-windows.yml"


def load_workflow():
    # BaseLoader preserves GitHub's `on` key instead of treating it as a bool.
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_windows_build_is_manual_and_publishes_by_default():
    triggers = load_workflow()["on"]
    assert set(triggers) == {"workflow_dispatch"}
    publish = triggers["workflow_dispatch"]["inputs"]["publish_release"]
    assert publish["type"] == "boolean"
    assert publish["default"] == "true"


def test_only_unpublished_installers_use_short_lived_artifacts():
    steps = load_workflow()["jobs"]["build-windows-x64"]["steps"]
    uploads = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@")]
    assert len(uploads) == 1
    assert uploads[0]["if"] == "${{ !inputs.publish_release }}"
    assert uploads[0]["with"]["retention-days"] == "3"
    assert uploads[0]["with"]["if-no-files-found"] == "error"


def test_release_publication_precedes_artifact_upload():
    steps = load_workflow()["jobs"]["build-windows-x64"]["steps"]
    release = next(s for s in steps if "gh release upload" in s.get("run", ""))
    artifact = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@"))
    assert release["if"] == "${{ inputs.publish_release }}"
    assert steps.index(release) < steps.index(artifact)
    assert release["run"].count("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }") == 2
