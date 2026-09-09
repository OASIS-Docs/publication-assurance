"""The URN-grandfather allowlist is a policy record, so pin it.

Naming Directives s8 permits URN-based namespaces only for TCs that used them
before 2012 (or their maintenance activities), with Project Administration's
approval. Every entry here is a decision with a date; a change to the set is a
policy change and must be deliberate.
"""
import importlib.util
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "pub-check" / "oasis_pub_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("oasis_pub_check", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_urn_grandfather_allowlist_is_exactly_the_approved_set():
    mod = _load()
    assert mod.XML_NS_URN_GRANDFATHER_TCS == frozenset({
        "ubl",    # pre-2012 URN namespaces
        "xacml",  # pre-2012 URN namespaces (urn:oasis:names:tc:xacml:1.0:, 2003)
        "acal",   # same TC, renamed 19 Aug 2026; urn:oasis:names:tc:acal: granted 20 Oct 2025
    })


def test_urn_grandfather_allowlist_is_immutable_and_lowercase():
    mod = _load()
    assert isinstance(mod.XML_NS_URN_GRANDFATHER_TCS, frozenset)
    assert all(tc == tc.lower() for tc in mod.XML_NS_URN_GRANDFATHER_TCS)
