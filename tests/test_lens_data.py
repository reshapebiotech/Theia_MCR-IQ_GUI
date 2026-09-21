"""Tests for the lens data model."""

from __future__ import annotations

import pytest

from theia_mcr_iq import lens_data, resources
from theia_mcr_iq.lens_data import LensNotFoundError, LensVariant


@pytest.fixture
def variants() -> dict[str, LensVariant]:
    return lens_data.flatten(resources.packaged_lens_data())


def test_flatten_packaged_table(variants: dict[str, LensVariant]) -> None:
    assert len(variants) == 12
    assert sum(k.startswith("TL1250_") for k in variants) == 7
    assert sum(k.startswith("TL410_") for k in variants) == 4
    assert sum(k.startswith("TL936_") for k in variants) == 1


def test_variant_merges_family_values(variants: dict[str, LensVariant]) -> None:
    lens = variants["TL1250_N6"]
    assert lens.name == "TL1250P N6"
    assert lens.fam == "TW90"
    assert (
        lens.zoom_steps,
        lens.zoom_pi,
        lens.focus_steps,
        lens.focus_pi,
        lens.iris_steps,
    ) == (
        3227,
        3119,
        8390,
        7959,
        75,
    )
    assert lens.has_irc and lens.has_pi


def test_feature_flags(variants: dict[str, LensVariant]) -> None:
    assert not variants["TL1250_N3"].has_irc
    assert not variants["TL1250_N3"].has_pi
    assert variants["TL1250_N4"].has_irc
    assert not variants["TL1250_N4"].has_pi


def test_irc_labels(variants: dict[str, LensVariant]) -> None:
    assert variants["TL1250_940VN6"].irc_labels() == (
        lens_data.IRC_FILTER_LABELS["vis"],
        lens_data.IRC_FILTER_LABELS["940"],
    )
    assert variants["TL1250_N5"].irc_labels() == ("Filter 1", "Filter 2")


def test_flatten_skips_non_dict_entries() -> None:
    assert (
        lens_data.flatten(
            {
                "comment": "x",
                "TLX": {
                    "fam": "T",
                    "zoomSteps": 1,
                    "zoomPI": 1,
                    "focusSteps": 1,
                    "focusPI": 1,
                    "irisSteps": 1,
                },
            }
        )
        == {}
    )


def test_resolve_by_key_name_and_case(variants: dict[str, LensVariant]) -> None:
    assert lens_data.resolve_lens("TL410_R6", variants).key == "TL410_R6"
    assert lens_data.resolve_lens("TL410P R6", variants).key == "TL410_R6"
    assert lens_data.resolve_lens("tl410p r6", variants).key == "TL410_R6"
    with pytest.raises(LensNotFoundError):
        lens_data.resolve_lens("nope", variants)


def test_migrate_lens_key(variants: dict[str, LensVariant]) -> None:
    assert lens_data.migrate_lens_key("TL936_R6", variants) == "TL936_R6"
    assert lens_data.migrate_lens_key("TL936P R6", variants) == "TL936_R6"
    assert lens_data.migrate_lens_key("TL1250P Nx", variants) == "TL1250_N6"
    assert lens_data.migrate_lens_key("", variants) == "TL1250_N6"
    assert lens_data.migrate_lens_key("x", {}) == ""


def test_compatible_families() -> None:
    assert lens_data.compatible_families("TW90") == {"TW90", "TW91"}
    assert lens_data.compatible_families("TW50") == {"TW50"}
