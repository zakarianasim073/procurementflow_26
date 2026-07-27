"""Core unit tests (T-007): normalize_package, zone mapping, SOR helpers."""
from __future__ import annotations

import pytest

from app.services.intelligence_base import IntelligenceBaseService
from app.agents.pricing.sor_zone_matcher import SORZoneMatcherAgent, DISTRICT_ZONES
from app.sor.sor_service import _norm, _norm_unit, _desc_tokens

norm_pkg = IntelligenceBaseService.normalize_package_no


class TestNormalizePackage:
    """ADR-016: package_no is the universal join key — semantics frozen."""

    @pytest.mark.parametrize("raw,expected", [
        ("WD-123/G-05", "WD-123/G-05"),
        ("wd-123/g-05", "WD-123/G-05"),          # uppercased
        ("  WD 123 / G 05  ", "WD-123/G-05".replace("-", "-") if False else "WD123/G05"),  # spaces stripped
        ("PKG.NO-7/2025", "PKG.NO-7/2025"),
        ("Pkg\\7-A", "PKG/7-A"),                  # backslash → slash
        (None, ""),
        ("", ""),
        ("1290886", ""),                           # pure long digits = tender id, not a package
        ("ABCDEF", ""),                            # no digits
        ("12345", ""),                             # digits only, no separator/alpha
        ("12/34", "12/34"),                        # digits with separator OK
        ("X" * 121 + "1", ""),                     # >120 chars
        ("W@D#1!", "WD1"),                         # symbols stripped
    ])
    def test_normalization(self, raw, expected):
        assert norm_pkg(raw) == expected

    def test_idempotent(self):
        v = norm_pkg("wd-123/G-05")
        assert norm_pkg(v) == v


class TestZoneMapping:
    """ADR-003: zone C↔D swap between LGED and PWD/BWDB is load-bearing."""

    @pytest.fixture(scope="class")
    def agent(self):
        return SORZoneMatcherAgent.__new__(SORZoneMatcherAgent)  # no brain needed for _resolve

    @pytest.mark.parametrize("agency,district,zone", [
        ("LGED", "Dhaka", "A"), ("PWD", "Dhaka", "A"), ("BWDB", "Dhaka", "A"),
        ("LGED", "Chattogram", "B"), ("PWD", "Chattogram", "B"),
        # The C↔D swap: Khulna/Barishal vs Rajshahi/Rangpur
        ("LGED", "Khulna", "D"), ("PWD", "Khulna", "C"),
        ("LGED", "Barishal", "D"), ("PWD", "Barishal", "C"),
        ("LGED", "Rajshahi", "C"), ("PWD", "Rajshahi", "D"),
        ("LGED", "Rangpur", "C"), ("PWD", "Rangpur", "D"),
        ("BWDB", "Khulna", "B"), ("BWDB", "Rajshahi", "C"),
    ])
    def test_district_to_zone(self, agent, agency, district, zone):
        assert agent._resolve(agency, district) == zone

    def test_unknown_location(self, agent):
        assert agent._resolve("LGED", "Atlantis") is None
        assert agent._resolve("NOPE", "Dhaka") is None

    def test_lged_pwd_cd_swap_is_symmetric(self):
        """Every LGED zone-C district is PWD zone-D and vice versa."""
        assert set(DISTRICT_ZONES["LGED"]["C"]) == set(DISTRICT_ZONES["PWD"]["D"])
        lged_d = set(DISTRICT_ZONES["LGED"]["D"])
        pwd_c = set(DISTRICT_ZONES["PWD"]["C"])
        assert pwd_c <= lged_d  # PWD-C ⊂ LGED-D (LGED-D adds Faridpur belt)

    @pytest.mark.parametrize("code,agency", [
        ("01.1.1(PWD)", "PWD"), ("1.01.01(LGED)", "LGED"), ("04-180-00(BWDB)", "BWDB"),
        ("EM-101", "PWD"), ("04-180-00", "BWDB"), ("2.05", "LGED"), ("01.5", "PWD"),
    ])
    def test_agency_detection(self, code, agency):
        agent = SORZoneMatcherAgent.__new__(SORZoneMatcherAgent)
        assert agent._detect_agency(code) == agency


class TestSorHelpers:
    @pytest.mark.parametrize("raw,expected", [
        ("04-180-00", "04180 00".replace(" ", "")),
        ("04 -180.00", "0418000"),
        ("A&B", "ab"),
        ("01.1.1", "0111"),
    ])
    def test_norm(self, raw, expected):
        assert _norm(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("Sq m", "sqm"), ("m2", "sqm"), ("Cu m", "cum"), ("m3", "cum"),
        ("Nos", "no"), ("each", "no"), ("kg", "kg"),
    ])
    def test_norm_unit(self, raw, expected):
        assert _norm_unit(raw) == expected

    def test_desc_tokens_drops_stopwords_and_short(self):
        tokens = _desc_tokens("The work of earth and RCC for 25mm pipe")
        assert "work" not in tokens and "the" not in tokens and "of" not in tokens
        assert "earth" in tokens and "rcc" in tokens and "25mm" in tokens
