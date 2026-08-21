"""Text canonicalisation shared across domains."""


def canonicalize_tag(value: str) -> str:
    """Reduce a free-text tag to its canonical stored form.

    Used for supplier skills and gig categories. Both are client-supplied free
    text that is later matched exactly, so both must agree on what "the same
    tag" means -- otherwise ``?category=Editing`` silently fails to match a gig
    stored as ``editing`` and the filter appears to work while returning nothing.

    Shared rather than inlined at each site despite only two callers. The test
    is not "is this duplicated?" but "do these change for the same reason?" --
    and they do: any future change to the canonical form (collapsing internal
    whitespace, normalising unicode) must apply to both simultaneously or
    cross-matching breaks. Two copies would drift; this cannot.
    """
    return value.strip().lower()
