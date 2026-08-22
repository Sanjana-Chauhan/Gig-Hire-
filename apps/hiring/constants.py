"""Domain constants for the hiring workflow.

The live-agreement cap lives in apps.common.constants instead: both this app
and accounts need it, and putting it here would make accounts import hiring
while hiring already imports accounts.
"""

# Business rule 10: rating is an integer between 1 and 5 inclusive.
#
# Named rather than inlined so the validators, the database CheckConstraint and
# the tests all derive the boundary from one place. A literal 5 in three files is
# three chances for a "1-10 stars" product decision to be half-applied.
RATING_MIN = 1
RATING_MAX = 5
