"""Decide recoverable release actions from independently observed state."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseState:
    pypi_exists: bool
    tag_exists: bool
    github_release_exists: bool
    github_release_has_artifacts: bool


@dataclass(frozen=True)
class ReleasePlan:
    build: bool
    publish: bool
    ensure_tag: bool
    ensure_release: bool

    def as_github_outputs(self) -> str:
        return "\n".join(
            (
                f"build={_format_bool(self.build)}",
                f"publish={_format_bool(self.publish)}",
                f"ensure_tag={_format_bool(self.ensure_tag)}",
                f"ensure_release={_format_bool(self.ensure_release)}",
            )
        )


def decide_release_actions(state: ReleaseState) -> ReleasePlan:
    publish = not state.pypi_exists
    ensure_tag = publish or (state.pypi_exists and not state.tag_exists)
    ensure_release = (
        publish
        or not state.github_release_exists
        or not state.github_release_has_artifacts
    )
    build = publish or ensure_release
    return ReleasePlan(
        build=build,
        publish=publish,
        ensure_tag=ensure_tag,
        ensure_release=ensure_release,
    )


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def _parse_bool(value: str) -> bool:
    if value.lower() in {"1", "true", "yes"}:
        return True
    if value.lower() in {"0", "false", "no"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, got {value!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pypi-exists", type=_parse_bool, required=True)
    parser.add_argument("--tag-exists", type=_parse_bool, required=True)
    parser.add_argument("--github-release-exists", type=_parse_bool, required=True)
    parser.add_argument(
        "--github-release-has-artifacts", type=_parse_bool, required=True
    )
    args = parser.parse_args()
    state = ReleaseState(
        pypi_exists=args.pypi_exists,
        tag_exists=args.tag_exists,
        github_release_exists=args.github_release_exists,
        github_release_has_artifacts=args.github_release_has_artifacts,
    )
    print(decide_release_actions(state).as_github_outputs())


if __name__ == "__main__":
    main()
