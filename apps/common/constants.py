"""Domain constants.

These are deliberately *not* in settings. A setting is something that legitimately
differs between environments; a constant is a domain invariant. Money is stored to
two decimal places in development, in test and in production -- making that
configurable would invite two deployments of the same service to disagree about
what a rate means.

The rule of thumb: if changing the value between environments would be a *bug*,
it is a constant, not a setting.
"""

from decimal import Decimal

# Monetary precision. 12 digits with 2 decimal places allows values up to
# 9,999,999,999.99, comfortably beyond any realistic gig budget while staying
# well inside what SQLite and PostgreSQL handle exactly.
MONEY_MAX_DIGITS = 12
MONEY_DECIMAL_PLACES = 2

# The specification requires monetary amounts to be strictly greater than zero.
# At two decimal places, "> 0" and ">= 0.01" describe exactly the same set of
# values, and the second is expressible as a validator.
MONEY_SMALLEST_POSITIVE = Decimal("0.01")
