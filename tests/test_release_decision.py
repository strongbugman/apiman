from scripts.release_decision import ReleaseState, decide_release_actions


def test_release_plan_publishes_when_pypi_version_is_absent() -> None:
    plan = decide_release_actions(
        ReleaseState(
            pypi_exists=False,
            tag_exists=True,
            github_release_exists=True,
            github_release_has_artifacts=True,
        )
    )

    assert plan.build is True
    assert plan.publish is True
    assert plan.ensure_tag is True
    assert plan.ensure_release is True


def test_release_plan_recovers_missing_tag_and_release_after_pypi_publish() -> None:
    plan = decide_release_actions(
        ReleaseState(
            pypi_exists=True,
            tag_exists=False,
            github_release_exists=False,
            github_release_has_artifacts=False,
        )
    )

    assert plan.build is True
    assert plan.publish is False
    assert plan.ensure_tag is True
    assert plan.ensure_release is True


def test_release_plan_refills_existing_release_without_artifacts() -> None:
    plan = decide_release_actions(
        ReleaseState(
            pypi_exists=True,
            tag_exists=True,
            github_release_exists=True,
            github_release_has_artifacts=False,
        )
    )

    assert plan.build is True
    assert plan.publish is False
    assert plan.ensure_tag is False
    assert plan.ensure_release is True


def test_release_plan_skips_complete_release_state() -> None:
    plan = decide_release_actions(
        ReleaseState(
            pypi_exists=True,
            tag_exists=True,
            github_release_exists=True,
            github_release_has_artifacts=True,
        )
    )

    assert plan.build is False
    assert plan.publish is False
    assert plan.ensure_tag is False
    assert plan.ensure_release is False
