"""Automated test suite for the GigHire API.

A package rather than a loose directory so that helper modules can be imported
as ``tests.endpoints`` and ``tests.assertions``. Without this file pytest puts
the tests directory itself on the import path, which makes those imports
ambiguous and requires every test file to have a globally unique name.
"""
