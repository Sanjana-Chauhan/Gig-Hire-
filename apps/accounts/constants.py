"""Domain constants for the accounts app."""

# Upper bounds on the skills list. These exist for input validation, not
# business reasons: without them a client can post a megabyte of JSON into a
# single column. Any unbounded, client-controlled collection is an availability
# risk, and validating its size is cheaper than paying for it later.
MAX_SKILLS_PER_SUPPLIER = 25
MAX_SKILL_LENGTH = 50

# Field lengths. Generous, but bounded -- an unbounded TextField for a name
# invites abuse and makes indexes unpredictable.
MAX_NAME_LENGTH = 150
MAX_CHANNEL_NAME_LENGTH = 150
