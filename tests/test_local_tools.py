"""Tests for deterministic support tools that require no network or API key."""

import json
import unittest

from support_agent.local_tools import _keywords, build_local_tools


class LocalToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tools = {tool.name: tool for tool in build_local_tools(object())}

    def test_keyword_normalization_matches_return_variants(self) -> None:
        self.assertIn("return", _keywords("Can this item be returned?"))

    def test_policy_search_returns_relevant_section(self) -> None:
        result = self.tools["search_support_policies"].invoke(
            {"question": "Can I return an unused product?"}
        )
        self.assertIn("## Returns", result)
        self.assertIn("30 days", result)

    def test_order_lookup_normalizes_id(self) -> None:
        result = self.tools["lookup_order"].invoke({"order_id": "ord-101"})
        order = json.loads(result)
        self.assertEqual("ORD-101", order["order_id"])
        self.assertEqual("shipped", order["status"])

    def test_order_lookup_rejects_invalid_shape(self) -> None:
        result = self.tools["lookup_order"].invoke({"order_id": "101"})
        self.assertEqual("Use an order ID in the form ORD-101.", result)


if __name__ == "__main__":
    unittest.main()
