# The Blue Red Candidate Case Dataset

Generated: 2026-06-03

This package belongs to the candidate case for a grounded AI quote assistant.

## Files

- `products.json`: product catalog with Turkish aliases, stock, price, substitutes and tags.
- `knowledge_entries.json`: policy and compatibility records that must be cited.
- `customers.json`: customer context for stock/backorder and price-tier decisions.
- `quotes.json`: initial draft quotes used by reference scenarios.
- `quote_items.json`: initial quote lines for duplicate, update and replacement cases.
- `price_rules.json`: discount rules to apply after quote mutations.
- `tool_contracts.json`: required tool/function call contracts.
- `tool_call_coverage.json`: tool-to-scenario coverage matrix.
- `golden_test_scenarios.json`: scenario-level expectations for tool calls and quote deltas.
- `seed.sql`: optional PostgreSQL demo schema and insert data under schema `case_seed`.

## Evaluation Intent

The dataset is intentionally small but adversarial. It includes out-of-stock products,
price-limit traps, Turkish aliases, duplicate quote lines, customer-specific
backorder rules, compatibility policies and discount rules. A passing solution should
use this data to prove every mandatory tool call works with persisted state changes.

