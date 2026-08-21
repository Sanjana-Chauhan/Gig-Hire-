"""Validation and normalisation for the supplier skills list."""

from django.core.exceptions import ValidationError

from apps.accounts.constants import MAX_SKILL_LENGTH, MAX_SKILLS_PER_SUPPLIER


def validate_skill_list(value) -> None:
    """Assert that ``value`` is a well-formed list of skill tags.

    Enforcement, not normalisation: this runs at the model layer, so it must
    accept anything legitimately already in the database and reject anything
    structurally wrong. Raising Django's ValidationError (rather than DRF's) is
    deliberate -- the project's exception handler translates it to a 400, and
    the model layer must not import DRF.
    """
    if not isinstance(value, list):
        raise ValidationError("Skills must be provided as a list.")

    if len(value) > MAX_SKILLS_PER_SUPPLIER:
        raise ValidationError(
            f"A supplier may list at most {MAX_SKILLS_PER_SUPPLIER} skills."
        )

    for skill in value:
        if not isinstance(skill, str):
            raise ValidationError("Each skill must be a string.")
        if not skill.strip():
            raise ValidationError("Skills cannot be blank.")
        if len(skill) > MAX_SKILL_LENGTH:
            raise ValidationError(
                f"Each skill must be at most {MAX_SKILL_LENGTH} characters."
            )


def normalize_skills(value: list[str]) -> list[str]:
    """Trim, lowercase and de-duplicate a skills list, preserving order.

    Normalisation belongs at the API boundary rather than in the model, because
    it is *sanitisation of external input*: the model's job is to reject invalid
    data, the boundary's job is to canonicalise valid data. Doing it here means
    ``"Video-Editing"``, ``" video-editing "`` and ``"video-editing"`` all become
    one tag, so filtering by skill later cannot miss records on a casing
    difference.

    Order is preserved rather than sorted: the order a supplier lists their
    skills in carries intent (most proficient first), and destroying it would be
    a lossy transformation done for no reason.

    This deliberately does *not* handle blank or non-string entries. Those are
    rejected upstream by ``validate_skill_list`` with a 400, rather than being
    quietly discarded here. A client sending ``[""]`` has a bug, and silently
    swallowing it would hide that bug -- normalisation canonicalises valid
    input, it does not repair invalid input.
    """
    seen: set[str] = set()
    normalized: list[str] = []
    for skill in value:
        canonical = skill.strip().lower()
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
    return normalized
