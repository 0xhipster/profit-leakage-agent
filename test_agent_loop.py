"""Free test of the agent loop. No internet, no API key, no cost.

A pretend Claude follows a fixed script. We check that the loop runs the
real tools, sends results back, handles a mistake, and obeys the step cap.

Run: python test_agent_loop.py superstore.csv
"""

import sys
from types import SimpleNamespace

import agent


def text_reply(text, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=100, output_tokens=20),
    )


def tool_reply(call_id, tool_name, **inputs):
    block = SimpleNamespace(type="tool_use", id=call_id, name=tool_name, input=inputs)
    return SimpleNamespace(
        content=[block], stop_reason="tool_use", usage=SimpleNamespace(input_tokens=100, output_tokens=20)
    )


class PretendClaude:
    """Gives out scripted replies one by one and remembers what it was sent."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        # Keep a snapshot of the message list as it was at this moment.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.script.pop(0)


DUPLICATES = ["Order.ID", "Product.ID", "Customer.ID", "Order.Date", "Sales", "Quantity", "Discount", "Profit", "Shipping.Cost"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data_path = sys.argv[1]
    problems = []

    # Test 1: the normal path, including one deliberate mistake (a table that does not exist).
    script = [
        tool_reply("a1", "load_data"),
        tool_reply("a2", "clean_data", drop_columns=["Market2", "weeknum"],
                   date_columns=["Order.Date", "Ship.Date"], duplicate_columns=DUPLICATES),
        tool_reply("a3", "calculate_by_group", group_by="Discount", cutoffs=[0, 0.2]),
        tool_reply("a4", "calculate_by_group", group_by="Category", table="nonexistent"),
        tool_reply("a5", "export_table", table="result_1", name="test_loop_discount_bands"),
        tool_reply("a6", "make_bar_chart", table="result_1", label_column="Discount band", value_column="margin_pct",
                   highlight="above 0.2", title="Discounts over 20% are associated with a margin of -42.21%",
                   subtitle="Profit margin by discount band, 2011 to 2014 (profit / sales, after adding up)",
                   source="Source: Global Superstore (Kaggle, fatihilhan). Margin = total profit / total sales.",
                   number_format="percent", name="test_loop_discount_chart"),
        text_reply("Pretend final answer."),
    ]
    claude = PretendClaude(script)
    final = agent.run_agent(claude, "pretend-model", data_path, "Test question", log=print)
    if final != "Pretend final answer.":
        problems.append("Test 1: final answer not returned")
    if len(claude.calls) != 7:
        problems.append("Test 1: expected 7 calls to Claude, got " + str(len(claude.calls)))
    # The mistake must have been sent back to Claude as an error, not crash the run.
    sent_back = claude.calls[4]["messages"][-1]["content"][0]
    if not sent_back.get("is_error") or "nonexistent" not in sent_back["content"]:
        problems.append("Test 1: bad table name was not reported back to Claude as an error")
    if "Discount band" not in claude.calls[5]["messages"][-1]["content"][0]["content"]:
        problems.append("Test 1: result_1 was not the discount band table")

    # Test 2: the step cap. Claude keeps asking for tools; after 2 rounds it must be told to stop.
    script = [
        tool_reply("b1", "load_data"),
        tool_reply("b2", "clean_data"),
        text_reply("Findings written at the cap."),
    ]
    claude = PretendClaude(script)
    final = agent.run_agent(claude, "pretend-model", data_path, "Test question", max_steps=2, log=print)
    last = claude.calls[-1]
    if final != "Findings written at the cap.":
        problems.append("Test 2: final answer after cap not returned")
    if last.get("tool_choice") != {"type": "none"}:
        problems.append("Test 2: tools were not switched off at the cap")
    if len(claude.calls) != 3:
        problems.append("Test 2: expected 3 calls to Claude, got " + str(len(claude.calls)))

    # Test 3: the ratio, bin and date options, run through the agent, plus the ways they can be misused.
    script = [
        tool_reply("c1", "load_data"),
        tool_reply("c2", "clean_data", drop_columns=["Market2", "weeknum"],
                   date_columns=["Order.Date", "Ship.Date"], duplicate_columns=DUPLICATES),
        tool_reply("c3", "calculate_by_group", ratio_of=["Shipping.Cost", "Sales"], bin_width=0.05),
        tool_reply("c4", "calculate_by_group", group_by="Order.Date", date_part="year"),
        tool_reply("c5", "calculate_by_group", ratio_of=["Shipping.Cost", "Sales"]),
        tool_reply("c6", "calculate_by_group", group_by="Order.Date", cutoffs=[1], bin_width=1),
        tool_reply("c7", "calculate_by_group", cutoffs=[0, 0.2]),
        tool_reply("c8", "calculate_by_group", group_by="Ship.Mode", date_part="year"),
        text_reply("Pretend final answer 3."),
    ]
    claude = PretendClaude(script)
    agent.run_agent(claude, "pretend-model", data_path, "Test question", log=print)

    def sent(call_index):
        return claude.calls[call_index]["messages"][-1]["content"][0]

    shipping = sent(3)["content"]
    if "undefined (denominator is 0 or missing) | 1 |" not in shipping or "YES" not in shipping.split("Reconciliation")[1]:
        problems.append("Test 3: shipping share bins did not keep the zero-sales row or did not reconcile")
    if "0 to under 0.05 | 7,183 |" not in shipping:
        problems.append("Test 3: lowest shipping share bin is not 7,183 rows")
    years = sent(4)["content"]
    if "2014 | 17,531 |" not in years or "YES" not in years.split("Reconciliation")[1]:
        problems.append("Test 3: year of Order.Date did not give 17,531 rows for 2014 or did not reconcile")
    for index, label, words in (
        (5, "ratio without bins", "cutoffs or bin_width"),
        (6, "cutoffs together with bin_width", "not both"),
        (7, "no group_by", "Give group_by"),
        (8, "date_part on a text column", "not a date column"),
    ):
        reply = sent(index)
        if not reply.get("is_error") or words not in reply["content"]:
            problems.append("Test 3: " + label + " was not reported back to Claude as a plain error")

    # Test 4: filters through the agent, a good call and five ways of misusing them.
    script = [
        tool_reply("d1", "load_data"),
        tool_reply("d2", "clean_data", drop_columns=["Market2", "weeknum"],
                   date_columns=["Order.Date", "Ship.Date"], duplicate_columns=DUPLICATES),
        tool_reply("d3", "calculate_by_group", group_by="Year", filters=[{"column": "Discount", "above": 0.2}]),
        tool_reply("d4", "calculate_by_group", group_by="Year", filters=[{"column": "Nope", "equals": "x"}]),
        tool_reply("d5", "calculate_by_group", group_by="Year", filters=[{"column": "Sub.Category", "equals": "Sofas"}]),
        tool_reply("d6", "calculate_by_group", group_by="Year", filters=[{"column": "Discount", "above": 0.2, "equals": 1}]),
        tool_reply("d7", "calculate_by_group", group_by="Year", filters=[{"column": "Segment", "above": 3}]),
        tool_reply("d8", "calculate_by_group", group_by="Year", filters=[{"column": "Order.Date", "equals": "2011-01-07"}]),
        text_reply("Pretend final answer 4."),
    ]
    claude = PretendClaude(script)
    agent.run_agent(claude, "pretend-model", data_path, "Test question", log=print)

    def sent4(call_index):
        return claude.calls[call_index]["messages"][-1]["content"][0]

    good = sent4(3)["content"]
    if "Rows kept: 11,328 of 51,290" not in good or "add back to the filtered rows: YES" not in good:
        problems.append("Test 4: the discount filter did not keep 11,328 rows or did not reconcile")
    for index, label, words in (
        (4, "unknown filter column", "Filter column not found"),
        (5, "filter that leaves no rows", "leaves 0 rows"),
        (6, "two operators in one condition", "exactly one of"),
        (7, "above on a text column", "needs a number column"),
        (8, "filter on a date column", "date column is not supported"),
    ):
        reply = sent4(index)
        if not reply.get("is_error") or words not in reply["content"]:
            problems.append("Test 4: " + label + " was not reported back to Claude as a plain error")

    print("\n" + "=" * 40)
    print("LOOP TEST RESULT: " + ("ALL PASSED" if not problems else "PROBLEMS FOUND"))
    for problem in problems:
        print(" - " + problem)


if __name__ == "__main__":
    main()
