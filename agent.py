"""The profit leakage agent: Claude plus five tools, in a loop.

How it works, in one paragraph:
Claude gets a set of instructions, a menu of five tools and a question.
Each round, Claude either asks for a tool or writes its final answer.
When it asks for a tool, this script runs the tool (plain code, all the
arithmetic happens here) and sends the text result back. This repeats
until Claude writes its answer or the step cap is reached.

Run it like this (from the profit-agent folder, with .venv active):
    python agent.py superstore.csv
Optional: a model name, then a question in quotes.
"""

import datetime
import os
import sys

import tools

DEFAULT_MODEL = "claude-haiku-5-5"
MAX_STEPS = 15          # the step cap: most rounds Claude gets
MAX_TOKENS = 4000       # longest single reply Claude may write
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
DEFAULT_QUESTION = (
    "Which products, regions or customer segments are losing money, "
    "and what should the business change?"
)

# The day-one brief. Claude reads this at the start of every round.
INSTRUCTIONS = """You are a business analyst agent. Your job is to find where a retail business loses profit and what it should change, using only the tools provided.

Rules:
1. Never calculate anything yourself. Every sum, margin and count must come from a tool. This includes adding, subtracting or combining two tool numbers. If you want a combined figure, ask a tool for it (for example with different cutoffs), or leave it out.
2. Every number in your findings must appear exactly in a tool result. If it is not there, do not state it. This includes numbers from memory, such as industry averages or competitor figures. Do not call a number high, low, average or typical unless a tool result gives the comparison. Never write a number into your answer and then say it is not a tool figure: leave it out.
3. Do not assume column names. Load the file first and use only what the load summary shows.
4. After every calculation, check the reconciliation line. If it says DO NOT TRUST, do not use those numbers, and say so. If a result has a WARNING line about missing values, say so in your findings and say what it affects.
5. Test more than one explanation. Say which are supported and which are not.
6. Write "associated with", never "caused by". The data cannot prove cause.
7. If the question cannot be answered from the data, or contains a claim the data contradicts, say so plainly. Check the facts in a question against the data before answering it.
8. If you choose a cutoff or band yourself, say that you chose it and what it is based on. Only say you looked at the data's values or range if a tool result showed them to you.
9. You have a limited number of tool calls. When told to stop, write your findings from what you have and list what you did not check.
10. Final answer: a headline with one number, two or three evidence points each tied to a tool result, then one line on what the data cannot tell us.
11. Before you say a group is not special, or that a pattern is the same everywhere, compare the group with the others using numbers that appear in tool results (for example, how many of its rows fall in the heavy-discount band, out of all its rows). If you did not test it, say so instead of saying there is no reason.

Currency is not verified, so call amounts "currency units". One row is one product line inside an order, so say "line items", not "orders"."""

# The tool menu. Claude knows the tools only through these descriptions.
TOOL_MENU = [
    {
        "name": "load_data",
        "description": (
            "Reads the data file for this run and describes it: row count, and for each column its name, "
            "type, missing values and distinct values, plus the lowest and highest value of number columns. Changes nothing. Call this first. "
            "Saves the table under the name 'raw'. Takes no inputs."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "clean_data",
        "description": (
            "Makes a cleaned copy of table 'raw' and saves it as 'clean'. Always drops columns that have "
            "only one value. You choose the rest after reading the load summary. "
            "drop_columns: columns that add nothing or repeat another column. "
            "date_columns: columns holding dates as text. "
            "duplicate_columns: the columns that together describe what one row contains (for example order, "
            "product, customer, date and amounts), used to find and remove duplicate rows. Never use a row number "
            "or any column that is different in every row, because it can never reveal a duplicate. "
            "Do not list a column in both drop_columns and duplicate_columns. "
            "Only drop a column if it adds nothing (empty, a row number, or an exact copy of a column you keep). "
            "Do not drop a column you might want to break results down by, such as year, region, category or segment. "
            "Reports rows and columns before and after. "
            "The raw table is never changed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drop_columns": {"type": "array", "items": {"type": "string"}},
                "date_columns": {"type": "array", "items": {"type": "string"}},
                "duplicate_columns": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "calculate_by_group",
        "description": (
            "Adds up sales and profit for each group, works out margin as total profit divided "
            "by total sales, counts the rows where profit is below 0 and gives the share of rows that lose money "
            "(loss_rate_pct), states how many groups lose money, and checks that the groups add back to "
            "the whole table. Sorted by profit, lowest first. Use it for any breakdown (category, region and "
            "so on). Ways to choose the groups: "
            "(1) group_by alone: one group per value of a column. "
            "(2) group_by plus cutoffs: bands of a number column such as a discount rate; cutoffs is an "
            "increasing list where each cutoff belongs to the band below it (cutoffs [0, 0.2] gives: up to and "
            "including 0, above 0 up to and including 0.2, above 0.2). "
            "(3) group_by plus bin_width: equal bins of a number column, each including its lower edge and "
            "excluding its upper edge (0.05 gives 0 to under 0.05, 0.05 to under 0.1, and so on). "
            "(4) ratio_of [numerator column, denominator column] plus cutoffs or bin_width: bands of one "
            "column divided by another, such as shipping cost divided by sales. Rows where the denominator is 0 "
            "or missing have no ratio and are reported as their own group, never dropped. "
            "(5) group_by set to a date column plus date_part ('year', 'quarter' or 'month'): groups by that "
            "part of the date; the column must already be converted with clean_data date_columns. "
            "Give only one of cutoffs and bin_width, and only one of ratio_of and date_part. "
            "Any of these can be combined with filters, to look inside one part of the data: a list of conditions, "
            "each with a column and exactly one of equals (a value), above (a number) or at_most (a number); all "
            "conditions must hold. The result states how many rows were kept, and the reconciliation is against "
            "the kept rows. Example: filters [{column: Sub.Category, equals: Tables}] with group_by Discount and "
            "cutoffs shows how discount bands behave inside Tables. Filtering on date columns is not supported; "
            "use a year column. Use filters to test an explanation inside a segment instead of guessing about it. "
            "Saves the result as 'result_1', 'result_2' and so on, and tells you which. Always read the "
            "reconciliation line."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {"type": "string", "description": "Column to group by. Not needed when ratio_of is given."},
                "table": {"type": "string", "description": "Saved table to use. Default 'clean'."},
                "cutoffs": {"type": "array", "items": {"type": "number"}},
                "bin_width": {"type": "number", "description": "Equal bin width for a number column or a ratio."},
                "ratio_of": {"type": "array", "items": {"type": "string"}, "description": "Two column names: [numerator, denominator]."},
                "date_part": {"type": "string", "enum": ["year", "quarter", "month"]},
                "filters": {
                    "type": "array",
                    "description": "Conditions that rows must meet to be used. All must hold.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "equals": {"type": ["string", "number"]},
                            "above": {"type": "number"},
                            "at_most": {"type": "number"},
                        },
                        "required": ["column"],
                    },
                },
                "sales_column": {"type": "string", "description": "Default 'Sales'."},
                "profit_column": {"type": "string", "description": "Default 'Profit'."},
            },
            "required": [],
        },
    },
    {
        "name": "export_table",
        "description": (
            "Saves one saved table as a CSV file in the output folder, then reads the file back and compares "
            "it with the table. Does no calculation. name: letters, digits, underscores and hyphens only, "
            "no .csv ending."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Name of a saved table, for example 'result_1'."},
                "name": {"type": "string"},
            },
            "required": ["table", "name"],
        },
    },
    {
        "name": "make_bar_chart",
        "description": (
            "Draws one bar chart from a saved result table, using a fixed template (bars sorted highest at the "
            "top, gray with one highlighted bar). Values come straight from the table. You write the title (one "
            "sentence stating the conclusion, true to the plotted values), the subtitle (what is measured) and "
            "the source line. label_column and value_column must be columns of the table. highlight must match "
            "one label exactly. number_format is 'percent', 'number' or 'decimal': use 'percent' for a margin_pct column "
            "and 'number' for sales, profit and counts. Write the title, subtitle and source in a neutral voice, "
            "never 'I' or 'me'. Needs 2 to 15 bars. "
            "If the table has more than 15 rows, give keep and keep_from ('lowest' or 'highest') to draw only "
            "that many bars from one end; the tool says how many were left out, so the title must not claim more "
            "than is shown. "
            "name: letters, digits, underscores and hyphens only. You cannot see the picture, so check the "
            "listed plotted values against your title."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "label_column": {"type": "string"},
                "value_column": {"type": "string"},
                "highlight": {"type": "string"},
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "source": {"type": "string"},
                "number_format": {"type": "string", "enum": ["percent", "number", "decimal"]},
                "name": {"type": "string"},
                "keep": {"type": "integer", "description": "Draw only this many bars (2 to 15)."},
                "keep_from": {"type": "string", "enum": ["lowest", "highest"]},
            },
            "required": ["table", "label_column", "value_column", "highlight", "title", "subtitle", "source", "name"],
        },
    },
]


def get_table(state, name):
    """Find a saved table by name, or say which names exist."""
    if name not in state:
        available = ", ".join(sorted(state)) if state else "none yet"
        raise ValueError("No saved table called '" + str(name) + "'. Saved tables: " + available)
    return state[name]


def run_tool(name, arguments, state, data_path):
    """Run one tool. Returns (text, is_error). Errors go back to Claude as text."""
    try:
        if name == "load_data":
            table, summary = tools.load_data(data_path)
            state["raw"] = table
            return summary + "\n\nSaved as table: raw", False

        if name == "clean_data":
            cleaned, report = tools.clean_data(
                get_table(state, "raw"),
                drop_columns=arguments.get("drop_columns"),
                date_columns=arguments.get("date_columns"),
                duplicate_columns=arguments.get("duplicate_columns"),
            )
            state["clean"] = cleaned
            return report + "\n\nSaved as table: clean", False

        if name == "calculate_by_group":
            grouped, summary = tools.calculate_by_group(
                get_table(state, arguments.get("table", "clean")),
                arguments.get("group_by"),
                sales_column=arguments.get("sales_column", "Sales"),
                profit_column=arguments.get("profit_column", "Profit"),
                cutoffs=arguments.get("cutoffs"),
                bin_width=arguments.get("bin_width"),
                ratio_of=arguments.get("ratio_of"),
                date_part=arguments.get("date_part"),
                filters=arguments.get("filters"),
            )
            result_name = "result_" + str(sum(1 for key in state if key.startswith("result_")) + 1)
            state[result_name] = grouped
            return summary + "\n\nSaved as table: " + result_name, False

        if name == "export_table":
            path, summary = tools.export_table(
                get_table(state, arguments["table"]), arguments["name"], folder=OUTPUT_FOLDER
            )
            return summary, False

        if name == "make_bar_chart":
            path, summary = tools.make_bar_chart(
                get_table(state, arguments["table"]),
                arguments["label_column"],
                arguments["value_column"],
                arguments["highlight"],
                arguments["title"],
                arguments["subtitle"],
                arguments["source"],
                number_format=arguments.get("number_format", "number"),
                name=arguments["name"],
                folder=OUTPUT_FOLDER,
                keep=arguments.get("keep"),
                keep_from=arguments.get("keep_from", "lowest"),
            )
            return summary, False

        return "ERROR: there is no tool called " + str(name), True
    except KeyError as problem:
        return "ERROR: an input or a column was not found: " + str(problem), True
    except Exception as problem:
        return "ERROR: " + str(problem), True


def run_agent(client, model, data_path, question, max_steps=MAX_STEPS, log=print):
    """The loop. Returns Claude's final text."""
    state = {}
    messages = [{
        "role": "user",
        "content": "Data file for this run: " + os.path.basename(data_path) + "\nQuestion: " + question,
    }]
    input_tokens = 0
    output_tokens = 0
    final_text = ""
    finished = False

    for step in range(1, max_steps + 1):
        log("\n===== Round " + str(step) + " of at most " + str(max_steps) + " =====")
        response = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=INSTRUCTIONS, tools=TOOL_MENU, messages=messages
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text" and block.text.strip():
                log("Claude says: " + block.text)

        if response.stop_reason != "tool_use":
            final_text = "\n".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                log("WARNING: the answer was cut off because it hit the length limit.")
            finished = True
            break

        results = []
        for block in response.content:
            if block.type == "tool_use":
                log("\nTool asked for: " + block.name + "  inputs: " + str(block.input))
                text, is_error = run_tool(block.name, block.input, state, data_path)
                log("Tool result:\n" + text)
                results.append({
                    "type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error,
                })
        messages.append({"role": "user", "content": results})

    if not finished:
        log("\n===== STEP CAP REACHED: asking Claude to write its findings now =====")
        messages[-1]["content"].append({
            "type": "text",
            "text": "You have used all your tool calls. Do not ask for more tools. Write your findings now "
                    "from the tool results above, and list what you did not check.",
        })
        response = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=INSTRUCTIONS, tools=TOOL_MENU,
            tool_choice={"type": "none"}, messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        final_text = "\n".join(b.text for b in response.content if b.type == "text")

    log("\n===== FINAL ANSWER =====\n" + final_text)
    log("\nTokens used this run: " + format(input_tokens, ",") + " in, " + format(output_tokens, ",") + " out")
    return final_text


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print("Usage: python agent.py superstore.csv [model] [question]")
        return
    data_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    question = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_QUESTION
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set in this window. Close PowerShell, open a new one, and try again.")
        return

    import anthropic
    client = anthropic.Anthropic()

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    transcript_path = os.path.join(OUTPUT_FOLDER, "run_" + stamp + ".txt")
    with open(transcript_path, "w", encoding="utf-8") as transcript:
        def log(text):
            print(text)
            transcript.write(text + "\n")
            transcript.flush()
        log("Model: " + model + "\nQuestion: " + question)
        run_agent(client, model, data_path, question, log=log)
    print("\nFull record saved to: " + transcript_path)


if __name__ == "__main__":
    main()
