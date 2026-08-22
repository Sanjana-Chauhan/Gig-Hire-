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

# The platform trades in a single currency, so amounts carry no currency field.
#
# The specification never states a unit, which would be dangerous with more than
# one: a budget of 500 and a proposal of 450 look like agreement whether they
# mean dollars or rupees. Fixing the platform to one currency makes every amount
# comparable, which is how single-market marketplaces normally work.
#
# Named here rather than left implicit so that introducing a second currency is
# a visible change with an obvious starting point, rather than a hunt for every
# place an amount is compared.
PLATFORM_CURRENCY = "USD"

# Business rule 4: the most live agreements one supplier may hold at once.
#
# Lives in common rather than in hiring because two apps need it and neither
# owns it: the hiring workflow enforces it, and a supplier's availability is
# derived from it (a supplier at the cap is "busy"). Putting it in hiring would
# mean accounts importing hiring, which would make the two mutually dependent.
#
# A constant rather than a setting, by the usual test: two deployments of this
# service disagreeing about the cap would be a bug, not a configuration choice.
# A production system would very likely make it per-supplier though -- a
# verified supplier carrying more work than a new one -- which makes it tier
# data in the database rather than a module-level value. Named here so that
# change has one obvious starting point.
MAX_ACTIVE_CONTRACTS_PER_SUPPLIER = 3
