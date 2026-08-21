"""Domain constants for the hiring workflow."""

# Business rule 4: a supplier may hold at most this many active contracts.
#
# A constant rather than a setting, by the usual test: two deployments of this
# service disagreeing about the cap would be a bug, not a configuration choice.
#
# Note what a production system would do differently, though. This value would
# not differ per *environment*, but it very plausibly differs per *supplier* --
# a verified or premium supplier might carry more work than a new one. That
# makes it tier data belonging in the database, not a module-level constant.
# Named here so the transition is a single, obvious edit rather than a hunt for
# a literal 3 scattered through the service layer.
MAX_ACTIVE_CONTRACTS_PER_SUPPLIER = 3
