"""Pure lens data model: flatten the limits table into variants and resolve user selections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IRC_FILTER_LABELS: dict[str, str] = {
    "vis": "Visible only\nfilter",
    "clear": "Clear filter\n(visible + IR) ",
    "850": "850nm BP\nfilter",
    "940": "940nm long\npass filter",
}

# Lens variant family tokens accepted for each calibration file family token.
FAMILY_COMPATIBILITY: dict[str, set[str]] = {
    "TW90": {"TW90", "TW91"},
}

# Lens identifiers written by releases up to v3.1.0, mapped to current variant keys.
LEGACY_LENS_ALIASES: dict[str, str] = {
    "TL410P Rx": "TL410_R6",
    "TL936P Rx": "TL936_R6",
    "TL1250P Nx": "TL1250_N6",
    "TL1250P Rx": "TL1250_N6",
    "TL410P Nx": "TL410_R6",
}


class LensNotFoundError(LookupError):
    """Raised when a lens key or display name matches no variant."""


@dataclass(frozen=True)
class LensVariant:
    """One selectable lens model with its motor extents and feature set."""

    key: str
    name: str
    fam: str
    zoom_steps: int
    zoom_pi: int
    focus_steps: int
    focus_pi: int
    iris_steps: int
    has_irc: bool = False
    has_pi: bool = False
    filter1: str = ""
    filter2: str = ""

    def irc_labels(self) -> tuple[str, str]:
        """Button labels for the two IRC filter positions, generic when the lens has no IRC."""
        labels = []
        for index, filter_key in enumerate((self.filter1, self.filter2), start=1):
            default = f"Filter {index}"
            labels.append(
                IRC_FILTER_LABELS.get(filter_key.lower(), default)
                if self.has_irc
                else default
            )
        return labels[0], labels[1]


def flatten(raw: dict[str, Any]) -> dict[str, LensVariant]:
    """Turn the grouped limits table into `{family_variant: LensVariant}` in file order."""
    variants: dict[str, LensVariant] = {}
    for family_key, family in raw.items():
        if not isinstance(family, dict):
            continue
        variant_items = {
            k: v for k, v in family.items() if isinstance(v, dict) and "name" in v
        }
        common = {k: v for k, v in family.items() if k not in variant_items}
        for variant_key, variant in variant_items.items():
            record = {**common, **variant}
            features = record.get("featureSet") or {}
            key = f"{family_key}_{variant_key}"
            variants[key] = LensVariant(
                key=key,
                name=str(record.get("name", key)),
                fam=str(record.get("fam", "")),
                zoom_steps=int(record["zoomSteps"]),
                zoom_pi=int(record["zoomPI"]),
                focus_steps=int(record["focusSteps"]),
                focus_pi=int(record["focusPI"]),
                iris_steps=int(record["irisSteps"]),
                has_irc=bool(features.get("IRC", False)),
                has_pi=bool(features.get("PI", False)),
                filter1=str(features.get("filter1", "")),
                filter2=str(features.get("filter2", "")),
            )
    return variants


def resolve_lens(query: str, variants: dict[str, LensVariant]) -> LensVariant:
    """Find a variant by key or display name (case-insensitive); raise LensNotFoundError otherwise."""
    if query in variants:
        return variants[query]
    folded = query.strip().casefold()
    for variant in variants.values():
        if folded in (variant.key.casefold(), variant.name.casefold()):
            return variant
    raise LensNotFoundError(query)


def migrate_lens_key(saved: str, variants: dict[str, LensVariant]) -> str:
    """Map a saved lens identifier (key, display name or legacy alias) to a current key, else the first key."""
    if saved in variants:
        return saved
    for variant in variants.values():
        if variant.name == saved:
            return variant.key
    alias = LEGACY_LENS_ALIASES.get(saved, "")
    if alias in variants:
        return alias
    return next(iter(variants), "")


def compatible_families(cal_file_family: str) -> set[str]:
    """Lens family tokens a calibration file of `cal_file_family` may be used with."""
    return FAMILY_COMPATIBILITY.get(cal_file_family, {cal_file_family})
