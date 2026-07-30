"""Tests for the shared owner color palette."""

from charts.owner_colors import (
    OWNER_COLORS,
    color_for,
    owner_scale,
    resolve_owner_key,
)


def test_pinned_owners_are_stable():
    assert color_for("Amazon") == OWNER_COLORS["Amazon"]
    assert color_for("Google") == OWNER_COLORS["Google"]
    assert color_for("Meta") == OWNER_COLORS["Meta"]


def test_substring_operator_labels_map_to_canonical_owners():
    assert resolve_owner_key("Related Digital/Google") == "Google"
    assert resolve_owner_key("NorthPoint Development/Amazon") == "Amazon"
    assert resolve_owner_key("Wurldwide LLC/ Meta") == "Meta"
    assert color_for("Related Digital/Google") == color_for("Google")


def test_no_reds_in_pinned_palette():
    # Rough guard: none of the pinned hex values should sit in the red family
    # that would blend into the water-stress choropleth.
    for name, hex_color in OWNER_COLORS.items():
        if name == "Unknown":
            continue
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        assert not (r > 160 and g < 100 and b < 100), f"{name} looks too red: {hex_color}"


def test_owner_scale_keeps_amazon_color_across_domains():
    scale_top = owner_scale(["Amazon", "Google", "Meta"]).to_dict()
    scale_wide = owner_scale(["Amazon", "QTS", "xAI", "CoreWeave", "Oracle"]).to_dict()
    amazon_top = scale_top["range"][scale_top["domain"].index("Amazon")]
    amazon_wide = scale_wide["range"][scale_wide["domain"].index("Amazon")]
    assert amazon_top == amazon_wide == OWNER_COLORS["Amazon"]
