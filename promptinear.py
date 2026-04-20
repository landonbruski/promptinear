import json
import os
import sys
import termios
import time
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from message import Message
from prompt_analyzer import PromptAnalyzer
from scoring import letter_grade
from stats import weakest_dimension


# setting up the rich console so I can print colored stuff
# rich is a library, had to pip install it

console = Console()


# I found this banner on a website that turns text into ASCII art
# was gonna make my own but this looked way better

BANNER = r"""
 ____                            _   _
|  _ \ _ __ ___  _ __ ___  _ __ | |_(_)_ __   ___  __ _ _ __
| |_) | '__/ _ \| '_ ` _ \| '_ \| __| | '_ \ / _ \/ _` | '__|
|  __/| | | (_) | | | | | | |_) | |_| | | | |  __/ (_| | |
|_|   |_|  \___/|_| |_| |_| .__/ \__|_|_| |_|\___|\__,_|_|
                           |_|"""

SUBTITLE = ""


# these are the coaching tips I wrote up for when a dimension is weak
# I spent way too long studying these lol, tried to make them actually useful
# each one has a why, how to fix, and a before/after example

COACHING_TIPS = {
    "grounding": {
        "why": "Without concrete references like file paths, function names, or quoted errors, the AI has to search the whole codebase to guess what you meant. Each wrong guess burns tokens.",
        "fix": "Include the exact file path, function or variable name, line number, or paste the specific error message. Ground the request in something the AI can look up directly.",
        "before": "fix the bug in the parser",
        "after": "Fix the TypeError in data/parser.py in the parse_line function",
    },
    "context": {
        "why": "Without context, the AI has to guess what is happening and what you expect. It often guesses wrong, generates a fix for the wrong problem, then has to start over, doubling the token cost.",
        "fix": "Describe the current behavior and the expected behavior. Include error messages if you have them.",
        "before": "the login is broken",
        "after": "The login form returns a 500 error because the session token is None",
    },
    "actionability": {
        "why": "Vague requests force the AI to explore multiple approaches before settling on one. Each abandoned approach wastes tokens on code that gets thrown away.",
        "fix": "Start with a verb: fix, add, refactor, delete, rename. Tell the AI exactly what action to take.",
        "before": "the button doesn't look right",
        "after": "Change the submit button background from gray to #4f46e5 in style.css",
    },
    "clarity": {
        "why": "Words like 'maybe', 'stuff', and 'things' are ambiguous. The AI has to interpret your intent, and when it interprets wrong, you both waste tokens going back and forth.",
        "fix": "Replace vague words with exact names, values, or descriptions. Say what you mean precisely.",
        "before": "maybe change some of the stuff in the config",
        "after": "Set max_retries to 3 in config.py",
    },
    "efficiency": {
        "why": "Every word in your prompt costs input tokens. Greetings, pleasantries, and filler add cost without adding information the AI can act on.",
        "fix": "Cut greetings, hedging, and filler. Get straight to the task. You are not being rude. You are being efficient.",
        "before": "Hi! Could you please help me fix the login bug? Thanks!",
        "after": "Fix the login bug in auth.py: session expires after 1 request",
    },
    "structure": {
        "why": "When you combine multiple requests into one sentence, the AI has to figure out the priority and order. It may miss items or do them in the wrong order, requiring rework.",
        "fix": "Use numbered steps or bullet points for multi-part requests. Put the most important item first.",
        "before": "update the API and also the tests and change the error messages",
        "after": "1. Add /api/users endpoint  2. Return 404 if not found  3. Add test",
    },
}


# general tips for the Tips menu screen
# I could probably add more but 9 felt like enough for now

USAGE_TIPS = [
    {
        "title": "Control Context Churn",
        "dimensions": "Context, Efficiency, Structure",
        "guidance": "Start one chat per task. Keep each chat focused on one bug or feature, then end it. Before switching tasks, write a 5-10 line handoff note with: goal, files touched, open questions, and next command.",
    },
    {
        "title": "Ask for One Action",
        "dimensions": "Actionability, Clarity, Grounding",
        "guidance": "Use an explicit verb and target: 'Refactor parse_line in data/parser.py to return (record, errors)'. Avoid mixed requests in one sentence. If you need multiple changes, list them as numbered steps.",
    },
    {
        "title": "Add Concrete Constraints",
        "dimensions": "Grounding, Structure",
        "guidance": "State file paths, symbols, and limits up front: language level, style constraints, and what must not change. Example: 'Use functions + while loops only; keep Analyze flow unchanged.'",
    },
    {
        "title": "Use /compact Before Drift",
        "dimensions": "Efficiency, Context",
        "guidance": "When replies start repeating or getting long, run /compact. Then continue with one fresh message that restates current objective, acceptance checks, and next step so Claude keeps the right focus.",
    },
    {
        "title": "Use /clear for Hard Reset",
        "dimensions": "Context, Clarity",
        "guidance": "If the chat is off-track, run /clear and restart with a tight brief: objective, current state, constraints, and expected output format. Use this when compacted context still feels noisy.",
    },
    {
        "title": "Treat Summaries as Lossy",
        "dimensions": "Context, Clarity",
        "guidance": "After any summary or compact, re-add critical facts explicitly: exact file names, edge cases, and non-negotiable requirements. Never assume compressed context preserved every detail.",
    },
    {
        "title": "Cache-Aware Turn Timing",
        "dimensions": "Efficiency",
        "guidance": "Reply within a few minutes when iterating so conversation cache is more likely to help. Keep repeated boilerplate out of new turns; send only new facts and decisions to reduce token spend.",
    },
    {
        "title": "Rate-Limit Fallback Workflow",
        "dimensions": "Actionability, Efficiency, Structure",
        "guidance": "If rate-limited: 1) Save current status in a short handoff note. 2) Continue implementation in another model/tool using that note. 3) Return later and resume from the same checklist, not from memory.",
    },
    {
        "title": "Close Every Turn with Checks",
        "dimensions": "Structure, Actionability, Clarity",
        "guidance": "End requests with clear validation: what command to run, what output should appear, and what to do if it fails. This reduces rework loops and keeps fixes measurable.",
    },
]


def parse_weak_selection(picked, weak_count):
    chosen = []
    invalid = []
    parts = picked.replace(",", " ").split()

    for part in parts:
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= weak_count:
                if idx not in chosen:
                    chosen.append(idx)
            else:
                invalid.append(part)
        else:
            invalid.append(part)

    return chosen, invalid


def coaching_panel_for_dimension(dimension_name, dimension_score, position, total):
    tip = COACHING_TIPS.get(dimension_name)
    if tip is None:
        body = Text()
        body.append("No coaching tip found for this dimension.\n", style="red")
        body.append("Press [n] Next, [p] Prev, [b] Back", style="dim")
        return Panel(body, title="Coaching Drill-Down", border_style="yellow", padding=(1, 2))

    body = Text()
    body.append("Dimension: ", style="bold cyan")
    body.append(dimension_name.capitalize() + "\n", style="bold white")
    body.append("Score: ", style="bold cyan")
    body.append(str(dimension_score) + "\n", style="bold yellow")
    body.append("Selection: ", style="bold cyan")
    body.append(str(position) + " of " + str(total) + "\n\n", style="white")

    body.append("Why this is weak\n", style="bold red")
    body.append(tip["why"] + "\n\n", style="white")

    body.append("How to fix it\n", style="bold green")
    body.append(tip["fix"] + "\n\n", style="white")

    body.append("Before vs After\n", style="bold cyan")
    body.append("Before: ", style="bold red")
    body.append(tip["before"] + "\n", style="white")
    body.append("After: ", style="bold green")
    body.append(tip["after"] + "\n\n", style="white")

    body.append("Controls: [n] Next  [p] Prev  [b] Back", style="dim")

    return Panel(
        body,
        title="Coaching Drill-Down",
        border_style="cyan",
        padding=(1, 2),
    )


def run_coaching_drilldown(weak, selected_numbers):
    selected_items = []
    for idx in selected_numbers:
        selected_items.append(weak[idx - 1])

    current = 0
    while True:
        name = selected_items[current][0]
        score = selected_items[current][1]

        console.clear()
        show_header()
        console.print()
        console.print(
            coaching_panel_for_dimension(
                name,
                score,
                current + 1,
                len(selected_items),
            )
        )
        console.print()

        action = input("  Action (n/p/b): ").strip().lower()
        if action == "n":
            if current < len(selected_items) - 1:
                current = current + 1
            else:
                console.print("  [yellow]Already at last selected dimension.[/yellow]")
                input("  Press Enter to continue...")
        elif action == "p":
            if current > 0:
                current = current - 1
            else:
                console.print("  [yellow]Already at first selected dimension.[/yellow]")
                input("  Press Enter to continue...")
        elif action == "b":
            break
        else:
            console.print("  [red]Please use n, p, or b.[/red]")
            input("  Press Enter to continue...")


# below are my functions for loading and saving the history file
# I save it as json so it persists between runs

HISTORY_FILE = "history.json"


def load_history():
    # if the file doesnt exist yet I just make an empty one
    if not os.path.exists(HISTORY_FILE):
        # had a weird bug where the folder didnt exist so I make it here just in case
        data_dir = os.path.dirname(HISTORY_FILE)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
        save_history([])
        return []
    file = open(HISTORY_FILE, "r")
    text = file.read()
    file.close()
    if text.strip() == "":
        return []
    return json.loads(text)


def save_history(history):
    file = open(HISTORY_FILE, "w")
    file.write(json.dumps(history, indent=2))
    file.close()


def add_to_history(preview, grade, letter, tokens_wasted, dollars_wasted, weakest_name):
    history = load_history()
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "preview": preview,
        "grade": grade,
        "letter_grade": letter,
        "tokens_wasted": tokens_wasted,
        "dollars_wasted": dollars_wasted,
        "weakest": weakest_name,
    }
    history.append(record)
    save_history(history)
    return history


def history_top_weakest(history):
    counts = {}
    i = 0
    while i < len(history):
        weak = str(history[i].get("weakest", "unknown"))
        if weak in counts:
            counts[weak] = counts[weak] + 1
        else:
            counts[weak] = 1
        i = i + 1

    best_name = "N/A"
    best_count = 0
    for name in counts:
        count = counts[name]
        if count > best_count:
            best_name = name
            best_count = count

    return best_name, best_count


def history_average_letter(history):
    if len(history) == 0:
        return "N/A"

    grade_sum = 0.0
    i = 0
    while i < len(history):
        grade_sum = grade_sum + float(history[i].get("grade", 0))
        i = i + 1

    avg_grade = grade_sum / len(history)
    return letter_grade(avg_grade)


def sparkline(values, max_chars):
    """tiny bar graph using block characters"""
    blocks = "▁▂▃▄▅▆▇█"
    if len(values) == 0:
        return ""

    lo = values[0]
    hi = values[0]
    for v in values:
        if v < lo:
            lo = v
        if v > hi:
            hi = v

    spread = hi - lo
    if spread == 0:
        spread = 1.0

    chars = ""
    for v in values:
        idx = int((v - lo) / spread * 7)
        if idx > 7:
            idx = 7
        if idx < 0:
            idx = 0
        chars = chars + blocks[idx]

    return chars


def history_sparkline_text(history, count):
    """this builds the little trend line showing the last few grades in a row"""
    text = Text()
    if len(history) < 2:
        return text

    start = len(history) - count
    if start < 0:
        start = 0

    grades = []
    i = start
    while i < len(history):
        grades.append(safe_float(history[i].get("grade", 0), 0.0))
        i = i + 1

    line = sparkline(grades, count)
    text.append("Last " + str(len(grades)) + " grades: ", style="bold cyan")
    text.append(line, style="bold green")

    # putting the letter under each bar so the user can read what it means
    letters = ""
    for g in grades:
        letter = letter_grade(g)
        letters = letters + letter[0]
    text.append("\n")
    text.append("                " + letters, style="dim")
    return text


def history_summary_text(history):
    total = len(history)

    grade_sum = 0.0
    dollars_sum = 0.0
    i = 0
    while i < total:
        grade_sum = grade_sum + float(history[i].get("grade", 0))
        dollars_sum = dollars_sum + float(history[i].get("dollars_wasted", 0))
        i = i + 1

    avg_numeric = round(grade_sum / total, 1)
    avg_letter = history_average_letter(history)
    top_name, top_count = history_top_weakest(history)

    text = Text()
    text.append("Total analyses: ", style="bold cyan")
    text.append(str(total) + "\n", style="white")
    text.append("Average numeric grade: ", style="bold cyan")
    text.append(str(avg_numeric) + "\n", style="white")
    text.append("Average letter grade: ", style="bold cyan")
    text.append(avg_letter + "\n", style="white")
    text.append("Total estimated dollars wasted: ", style="bold cyan")
    text.append("$" + str(round(dollars_sum, 4)) + "\n", style="white")
    text.append("Top weakest dimension: ", style="bold cyan")
    text.append(top_name + " (" + str(top_count) + ")", style="white")
    return text


def history_recent_text(history, limit):
    text = Text()
    shown = 0
    i = len(history) - 1

    while i >= 0 and shown < limit:
        row = history[i]
        timestamp = str(row.get("timestamp", "N/A"))
        preview = str(row.get("preview", ""))
        grade = str(round(float(row.get("grade", 0)), 1))
        letter = str(row.get("letter_grade", "N/A"))
        weak = str(row.get("weakest", "N/A"))

        text.append(str(shown + 1) + ". ", style="bold cyan")
        text.append(timestamp + "\n", style="white")
        text.append("   Prompt: ", style="bold")
        text.append(preview + "\n", style="white")
        text.append("   Grade: ", style="bold")
        text.append(grade + " (" + letter + ")\n", style="white")
        text.append("   Weakest: ", style="bold")
        text.append(weak + "\n\n", style="white")

        shown = shown + 1
        i = i - 1

    if shown == 0:
        text.append("No history entries yet.", style="dim")

    return text


def safe_float(value, default_value):
    if value is None:
        return default_value
    return float(value)


def safe_int(value, default_value):
    if value is None:
        return default_value
    return int(value)


def flush_input():
    """clears any leftover keys in the input buffer, ran into this when users mashed keys during the animation"""
    if sys.stdin.isatty():
        termios.tcflush(sys.stdin, termios.TCIFLUSH)


def input_with_default(prompt_text, default_value):
    value = input(prompt_text)
    if value.strip() == "":
        return default_value
    return value


def performance_grade_distribution(history):
    buckets = {
        "A": 0,
        "B": 0,
        "C": 0,
        "D": 0,
        "F": 0,
    }

    i = 0
    while i < len(history):
        grade = safe_float(history[i].get("grade", 0), 0.0)
        if grade >= 90:
            buckets["A"] = buckets["A"] + 1
        elif grade >= 80:
            buckets["B"] = buckets["B"] + 1
        elif grade >= 70:
            buckets["C"] = buckets["C"] + 1
        elif grade >= 60:
            buckets["D"] = buckets["D"] + 1
        else:
            buckets["F"] = buckets["F"] + 1
        i = i + 1

    return buckets


def performance_weakest_counts(history):
    counts = {}
    i = 0
    while i < len(history):
        name = str(history[i].get("weakest", "unknown"))
        if name in counts:
            counts[name] = counts[name] + 1
        else:
            counts[name] = 1
        i = i + 1
    return counts


def performance_trend_data(history):
    total = len(history)
    if total < 2:
        return {
            "has_data": False,
            "status": "flat",
            "older_avg": 0.0,
            "newer_avg": 0.0,
            "delta": 0.0,
            "older_count": 0,
            "newer_count": 0,
        }

    split_index = total // 2
    if split_index == 0:
        split_index = 1

    older_sum = 0.0
    older_count = 0
    i = 0
    while i < split_index:
        older_sum = older_sum + safe_float(history[i].get("grade", 0), 0.0)
        older_count = older_count + 1
        i = i + 1

    newer_sum = 0.0
    newer_count = 0
    i = split_index
    while i < total:
        newer_sum = newer_sum + safe_float(history[i].get("grade", 0), 0.0)
        newer_count = newer_count + 1
        i = i + 1

    if older_count == 0 or newer_count == 0:
        return {
            "has_data": False,
            "status": "flat",
            "older_avg": 0.0,
            "newer_avg": 0.0,
            "delta": 0.0,
            "older_count": older_count,
            "newer_count": newer_count,
        }

    older_avg = round(older_sum / older_count, 1)
    newer_avg = round(newer_sum / newer_count, 1)
    delta = round(newer_avg - older_avg, 1)

    if delta > 1.0:
        status = "improving"
    elif delta < -1.0:
        status = "declining"
    else:
        status = "flat"

    return {
        "has_data": True,
        "status": status,
        "older_avg": older_avg,
        "newer_avg": newer_avg,
        "delta": delta,
        "older_count": older_count,
        "newer_count": newer_count,
    }


def performance_usage_totals(history):
    total_tokens = 0
    total_dollars = 0.0

    i = 0
    while i < len(history):
        total_tokens = total_tokens + safe_int(history[i].get("tokens_wasted", 0), 0)
        total_dollars = total_dollars + safe_float(history[i].get("dollars_wasted", 0), 0.0)
        i = i + 1

    avg_dollars = 0.0
    if len(history) > 0:
        avg_dollars = round(total_dollars / len(history), 4)

    return {
        "total_tokens": total_tokens,
        "total_dollars": round(total_dollars, 4),
        "avg_dollars": avg_dollars,
    }


def bar_chart_text(label_value_pairs, bar_char, max_bar_width, color_map):
    """horizontal bar chart function, I use it for the performance screen"""
    text = Text()

    # gotta find the biggest value first so my bars dont go off the screen
    max_val = 0
    for pair in label_value_pairs:
        if pair[1] > max_val:
            max_val = pair[1]
    if max_val == 0:
        max_val = 1

    for pair in label_value_pairs:
        label = pair[0]
        value = pair[1]
        fill = int(max_bar_width * value / max_val)
        if value > 0 and fill == 0:
            fill = 1

        color = color_map.get(label, "cyan")

        text.append(label.ljust(14), style="bold white")
        text.append(bar_char * fill, style=color)
        text.append(" " + str(value) + "\n", style="dim")

    return text


def performance_grade_distribution_text(history):
    buckets = performance_grade_distribution(history)
    pairs = [
        ("A (90-100)", buckets["A"]),
        ("B (80-89)", buckets["B"]),
        ("C (70-79)", buckets["C"]),
        ("D (60-69)", buckets["D"]),
        ("F (below 60)", buckets["F"]),
    ]
    colors = {
        "A (90-100)": "green",
        "B (80-89)": "cyan",
        "C (70-79)": "yellow",
        "D (60-69)": "dark_orange",
        "F (below 60)": "red",
    }
    return bar_chart_text(pairs, "█", 30, colors)


def performance_weakest_table_text(history):
    counts = performance_weakest_counts(history)

    order = ["clarity", "grounding", "actionability", "context", "efficiency", "structure"]
    pairs = []

    i = 0
    while i < len(order):
        key = order[i]
        if key in counts:
            pairs.append((key.capitalize(), counts[key]))
        i = i + 1

    for key in counts:
        if key not in order and key != "unknown":
            pairs.append((key.capitalize(), counts[key]))

    if len(pairs) == 0:
        text = Text()
        text.append("No data yet.", style="dim")
        return text

    yellow_colors = {}
    for pair in pairs:
        yellow_colors[pair[0]] = "yellow"
    return bar_chart_text(pairs, "▓", 30, yellow_colors)


def performance_trend_text(history):
    trend = performance_trend_data(history)
    text = Text()

    if not trend["has_data"]:
        text.append("Not enough data for trend summary.\n", style="yellow")
        text.append("Add at least 2 analyses to compare older vs newer performance.", style="dim")
        return text

    text.append("Older half average: ", style="bold cyan")
    text.append(str(trend["older_avg"]) + " (n=" + str(trend["older_count"]) + ")\n", style="white")
    text.append("Newer half average: ", style="bold cyan")
    text.append(str(trend["newer_avg"]) + " (n=" + str(trend["newer_count"]) + ")\n", style="white")
    text.append("Change (newer - older): ", style="bold cyan")
    text.append(str(trend["delta"]) + "\n", style="white")
    text.append("Status: ", style="bold cyan")

    if trend["status"] == "improving":
        text.append("improving", style="bold green")
    elif trend["status"] == "declining":
        text.append("declining", style="bold red")
    else:
        text.append("flat", style="bold yellow")

    return text


def performance_usage_text(history):
    usage = performance_usage_totals(history)
    text = Text()
    text.append("Total estimated tokens wasted: ", style="bold cyan")
    text.append(str(usage["total_tokens"]) + "\n", style="white")
    text.append("Total estimated dollars wasted: ", style="bold cyan")
    text.append("$" + str(usage["total_dollars"]) + "\n", style="white")
    text.append("Average dollars wasted per analysis: ", style="bold cyan")
    text.append("$" + str(usage["avg_dollars"]), style="white")
    return text


# little helpers for coloring the letter grade
# A should feel good (green), F should feel bad (red), you get the idea

def grade_color(letter):
    """picks a color for the letter grade, pretty self explanatory"""
    base = letter[0]
    if base == "A":
        return "green"
    if base == "B":
        return "cyan"
    if base == "C":
        return "yellow"
    if base == "D":
        return "dark_orange"
    return "red"


def styled_grade_text(score):
    """shows the letter grade with a colored background, makes it pop"""
    letter = letter_grade(score)
    color = grade_color(letter)
    text = Text()
    text.append(" " + letter + " ", style="bold white on " + color)
    text.append(" " + str(score), style="bold " + color)
    return text


# ok so I had to curve the scores because without this everyone was getting Ds and Fs
# like I tested it with a pretty decent prompt and got a 55 which felt wrong
# so I made these curves to bump up decent prompts to B or C range
# really bad ones below 35 still get an F though so its not like im trying to give everyone an A

def curve_grade(raw_score):
    if raw_score >= 95:
        return 99.0
    if raw_score >= 85:
        return 90.0 + (raw_score - 85.0) * 0.9
    if raw_score >= 70:
        return 80.0 + (raw_score - 70.0) * 0.67
    if raw_score >= 55:
        return 70.0 + (raw_score - 55.0) * 0.67
    if raw_score >= 40:
        return 60.0 + (raw_score - 40.0) * 0.67
    if raw_score >= 25:
        return 45.0 + (raw_score - 25.0) * 1.0
    return raw_score * 1.8


def curve_dimension(raw_score):
    if raw_score >= 90:
        return 95.0 + (raw_score - 90.0) * 0.5
    if raw_score >= 70:
        return 80.0 + (raw_score - 70.0) * 0.75
    if raw_score >= 50:
        return 65.0 + (raw_score - 50.0) * 0.75
    if raw_score >= 30:
        return 50.0 + (raw_score - 30.0) * 0.75
    return 35.0 + raw_score * 0.5


# my rough estimate of how many tokens and dollars a bad prompt wastes

def estimate_tokens_wasted(grade, word_count):
    input_tokens = round(word_count * 1.3)
    waste = round(4000 * (100 - grade) / 100)
    dollars = round(waste * 15 / 1000000, 4)
    return {
        "input_tokens": input_tokens,
        "tokens_wasted": waste,
        "dollars_wasted": dollars,
    }


# prints the banner at the top of every screen

def show_header():
    banner_text = Text(BANNER, style="bold cyan")
    console.print(Panel(banner_text, border_style="cyan", padding=(0, 2)))


# little stats line at the bottom, kinda like a status bar

def show_footer():
    history = load_history()
    count = len(history)

    if count == 0:
        stats_line = "Analyses: 0  |  Avg: N/A  |  Waste: $0.00"
    else:
        grade_sum = 0.0
        total_dollars = 0.0
        for record in history:
            grade_sum = grade_sum + record.get("grade", 0)
            total_dollars = total_dollars + record.get("dollars_wasted", 0)
        avg_grade = round(grade_sum / count, 1)
        avg_letter = letter_grade(avg_grade)
        stats_line = "Analyses: " + str(count) + "  |  Avg: " + avg_letter + " (" + str(avg_grade) + ")  |  Est. waste: $" + str(round(total_dollars, 2))

    console.print(Panel(stats_line, border_style="dim", style="dim"))


# the main menu at the bottom. I went with number keys cause its fast

def show_menu():
    menu = Text()
    menu.append("  [1]", style="bold cyan")
    menu.append(" Analyze  ")
    menu.append("[2]", style="bold cyan")
    menu.append(" History  ")
    menu.append("[3]", style="bold cyan")
    menu.append(" Tips  ")
    menu.append("[4]", style="bold cyan")
    menu.append(" Performance  ")
    menu.append("[H]", style="bold cyan")
    menu.append(" Help  ")
    menu.append("[Q]", style="bold red")
    menu.append(" Quit")
    console.print(menu)


# each function below is one of the screens. I probably shouldve split these into separate files
# but it was easier to keep them all here while I was building

def screen_welcome():
    history = load_history()
    count = len(history)

    body = Text()
    body.append("Paste any AI prompt to get an instant efficiency score.\n\n", style="white")
    body.append("How it works:\n", style="bold cyan")
    body.append("  1. Paste a prompt you've used (or plan to use)\n", style="white")
    body.append("  2. Get scored on 6 dimensions (clarity, grounding, etc.)\n", style="white")
    body.append("  3. See coaching tips to improve weak areas\n", style="white")
    body.append("  4. Track your progress over time\n\n", style="white")

    if count == 0:
        body.append("Press [1] to analyze your first prompt!", style="bold green")
    else:
        avg_letter = history_average_letter(history)
        body.append("You have ", style="dim")
        body.append(str(count), style="bold cyan")
        body.append(" analyses. Average grade: ", style="dim")
        body.append(avg_letter, style="bold cyan")

    console.print(Panel(body, title="Promptinear", border_style="cyan", padding=(1, 2)))


def run_single_analysis():
    """this is the big one, runs one analysis and shows all the results. kinda long ngl"""
    console.print(Panel(
        "Paste a prompt below, then press [bold cyan]Enter twice[/bold cyan] to submit.",
        title="Analyze",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()

    lines = []
    while True:
        if len(lines) == 0:
            line = input("  > ")
        else:
            line = input("    ")
        if line.strip() == "" and len(lines) > 0:
            break
        if line.strip() == "" and len(lines) == 0:
            continue
        lines.append(line)
    prompt_text = "\n".join(lines).strip()
    flush_input()

    if prompt_text == "":
        console.print()
        console.print("[bold red]No prompt entered.[/bold red]")
        input("  Press Enter to continue...")
        return None

    console.print()
    with console.status("[bold cyan]Scoring...[/bold cyan]", spinner="dots"):
        analyzer = PromptAnalyzer()
        message = Message("user", prompt_text)
        raw = analyzer.analyze(message)

    # curving the scores so grades feel fair, see curve_grade up top for the math
    curved = {}
    dim_names = ["clarity", "grounding", "actionability", "context", "efficiency", "structure"]
    for name in dim_names:
        curved[name] = round(curve_dimension(raw[name]), 1)
    curved["grade"] = round(curve_grade(raw["grade"]), 1)

    display_dims = dim_names + ["grade"]

    bar_width = 30
    steps = 12
    with Live(console=console, refresh_per_second=20) as live:
        for step in range(steps + 1):
            progress = step / steps
            bars = Text()

            for name in display_dims:
                score = curved[name]
                shown_score = round(score * progress, 1)
                shown_fill = int(bar_width * shown_score / 100)
                bar = "█" * shown_fill + "░" * (bar_width - shown_fill)

                if score >= 80:
                    color = "green"
                elif score >= 65:
                    color = "yellow"
                else:
                    color = "red"

                label = name.capitalize().ljust(13)
                bars.append(label + " ")
                bars.append(bar, style=color)
                bars.append(" " + str(shown_score).rjust(5) + "\n", style=color)

            letter_display = letter_grade(curved["grade"])
            title_color = grade_color(letter_display)

            live.update(
                Panel(
                    bars,
                    title="Prompt Scores  [bold white on " + title_color + "] " + letter_display + " [/bold white on " + title_color + "]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

            if step < steps:
                time.sleep(0.05)

    token_data = estimate_tokens_wasted(curved["grade"], message.word_count())
    token_text = Text()
    token_text.append("Grade: ", style="bold")
    grade_badge = styled_grade_text(curved["grade"])
    token_text.append_text(grade_badge)
    token_text.append("\n")
    token_text.append("Input tokens: ", style="bold")
    token_text.append(str(token_data["input_tokens"]) + "\n")
    token_text.append("Estimated wasted tokens: ", style="bold")
    token_text.append(str(token_data["tokens_wasted"]) + "\n")
    token_text.append("Estimated wasted cost: ", style="bold")
    token_text.append("$" + str(token_data["dollars_wasted"]))

    console.print()
    console.print(
        Panel(
            token_text,
            title="Token Impact",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # grabbing any dimensions below 70 so I can offer coaching on the weak ones
    # 70 is my cutoff, anything under that I consider a weak area
    weak = []
    for name in dim_names:
        if curved[name] < 70:
            weak.append((name, curved[name]))

    if weak:
        weak_text = Text()
        for i in range(len(weak)):
            weak_name = weak[i][0]
            weak_score = weak[i][1]
            weak_text.append(str(i + 1) + ". " + weak_name.capitalize() + " (" + str(weak_score) + ")\n")

        console.print()
        console.print(
            Panel(
                weak_text,
                title="Areas to Improve",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print("  [dim]Enter number(s) for coaching tips, or press Enter to skip[/dim]")
        picked = input_with_default("  > ", "")
        if picked.strip() != "":
            chosen, invalid = parse_weak_selection(picked.strip(), len(weak))

            if invalid:
                console.print("  [red]Ignored invalid selection(s): " + ", ".join(invalid) + "[/red]")

            if chosen:
                run_coaching_drilldown(weak, chosen)
    else:
        console.print()
        console.print(Panel("All dimensions look strong. Nice work!", title="Results", border_style="green", padding=(1, 2)))

    preview = message.summary(80)
    letter = letter_grade(curved["grade"])
    weak_name, _ = weakest_dimension({
        "clarity": curved["clarity"],
        "grounding": curved["grounding"],
        "actionability": curved["actionability"],
        "context": curved["context"],
        "efficiency": curved["efficiency"],
        "structure": curved["structure"],
    })
    add_to_history(
        preview,
        curved["grade"],
        letter,
        token_data["tokens_wasted"],
        token_data["dollars_wasted"],
        weak_name,
    )

    console.print()
    console.print("[dim]Analysis saved to history.[/dim]")
    console.print()
    show_footer()
    console.print()
    show_menu()
    console.print("  [bold cyan][A][/bold cyan] Analyze another")
    console.print()
    return input_with_default("  > ", "").strip().lower()


def screen_analyze():
    """keeps looping analyses so the user can do a bunch in a row without going back to the menu"""
    while True:
        result = run_single_analysis()
        if result is None:
            return "welcome"
        if result == "a" or result == "1":
            console.clear()
            show_header()
            console.print()
            continue
        if result == "2":
            return "history"
        if result == "3" or result == "t":
            return "tips"
        if result == "4":
            return "team"
        if result == "h":
            return "help"
        if result == "q" or result == "quit":
            return "quit"
        return "welcome"


def clear_history():
    confirm = input_with_default("  Are you sure? This deletes all history. (yes/no): ", "no").strip().lower()
    if confirm == "yes" or confirm == "y":
        save_history([])
        console.print("  [bold green]History cleared.[/bold green]")
    else:
        console.print("  [dim]Cancelled.[/dim]")
    input_with_default("  Press Enter to continue...", "")


EXAMPLE_PROMPT = "Fix the TypeError in data/parser.py in the parse_line function: it crashes when the input is an empty string"


def screen_history():
    history = load_history()

    if len(history) == 0:
        empty = Text()
        empty.append("No analyses saved yet.\n\n", style="yellow")
        empty.append("Try analyzing this example prompt:\n\n", style="white")
        empty.append("  " + EXAMPLE_PROMPT + "\n\n", style="italic cyan")
        empty.append("Press [bold cyan]1[/bold cyan] from the menu to get started.", style="dim")
        console.print(Panel(empty, title="History", border_style="yellow", padding=(1, 2)))
        return

    summary_panel = Panel(
        history_summary_text(history),
        title="History Summary",
        border_style="yellow",
        padding=(1, 2),
    )

    recent_panel = Panel(
        history_recent_text(history, 6),
        title="Recent Entries",
        border_style="cyan",
        padding=(1, 2),
    )

    console.print(summary_panel)

    spark = history_sparkline_text(history, 10)
    if spark.plain.strip() != "":
        console.print()
        console.print(Panel(spark, title="Trend", border_style="green", padding=(1, 2)))

    console.print()
    console.print(recent_panel)
    console.print()
    console.print("  [dim]Press [bold red]C[/bold red] to clear history, or Enter to go back[/dim]")
    action = input_with_default("  > ", "").strip().lower()
    if action == "c":
        clear_history()


def screen_tips():
    if len(USAGE_TIPS) == 0:
        console.print(Panel(
            "No tips found.",
            title="Tips",
            border_style="yellow",
            padding=(1, 2),
        ))
        return

    current = 0

    while True:
        tip = USAGE_TIPS[current]

        body = Text()
        body.append("Tip " + str(current + 1) + " of " + str(len(USAGE_TIPS)) + "\n", style="bold cyan")
        body.append("Dimensions: " + str(tip.get("dimensions", "N/A")) + "\n\n", style="dim")
        body.append(str(tip.get("guidance", "")) + "\n\n", style="white")
        body.append("Controls: [n] Next  [p] Prev  [b] Back", style="dim")

        console.clear()
        show_header()
        console.print()
        console.print(Panel(
            body,
            title=str(tip.get("title", "Tips")),
            border_style="blue",
            padding=(1, 2),
        ))
        console.print()

        action = input_with_default("  Action (n/p/b): ", "b").strip().lower()
        if action == "n":
            if current < len(USAGE_TIPS) - 1:
                current = current + 1
            else:
                console.print("  [yellow]Already at last tip.[/yellow]")
                input_with_default("  Press Enter to continue...", "")
        elif action == "p":
            if current > 0:
                current = current - 1
            else:
                console.print("  [yellow]Already at first tip.[/yellow]")
                input_with_default("  Press Enter to continue...", "")
        elif action == "b":
            break
        else:
            console.print("  [red]Please use n, p, or b.[/red]")
            input_with_default("  Press Enter to continue...", "")


def screen_team():
    history = load_history()

    if len(history) == 0:
        empty = Text()
        empty.append("No analyses saved yet.\n\n", style="yellow")
        empty.append("Try analyzing this example prompt:\n\n", style="white")
        empty.append("  " + EXAMPLE_PROMPT + "\n\n", style="italic cyan")
        empty.append("Analyze a few prompts, then come back to see your stats.", style="dim")
        console.print(Panel(empty, title="Performance Report", border_style="yellow", padding=(1, 2)))
        return

    # top bar with the summary stats, kinda my favorite part of this screen
    total = len(history)
    avg_letter = history_average_letter(history)
    usage = performance_usage_totals(history)
    top_name, top_count = history_top_weakest(history)

    summary = Text()
    summary.append(str(total), style="bold cyan")
    summary.append(" analyses  |  Avg: ", style="white")
    summary.append(avg_letter, style="bold cyan")
    summary.append("  |  $", style="white")
    summary.append(str(usage["total_dollars"]), style="bold cyan")
    summary.append(" estimated waste  |  Top weakness: ", style="white")
    summary.append(top_name.capitalize(), style="bold yellow")

    console.print(Panel(summary, title="Performance Report", border_style="magenta", padding=(0, 2)))
    console.print()

    console.print(Panel(
        performance_grade_distribution_text(history),
        title="Grade Distribution",
        border_style="magenta",
        padding=(1, 2),
    ))
    console.print()
    console.print(Panel(
        performance_weakest_table_text(history),
        title="Weakest Areas",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()
    console.print(Panel(
        performance_trend_text(history),
        title="Trend",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()
    console.print(Panel(
        performance_usage_text(history),
        title="Token Usage",
        border_style="yellow",
        padding=(1, 2),
    ))


def screen_help():
    body = Text()

    body.append("Main Menu Keys\n", style="bold cyan")
    body.append("1  Analyze\n", style="white")
    body.append("2  History\n", style="white")
    body.append("3  Tips\n", style="white")
    body.append("4  Performance\n", style="white")
    body.append("H  Help\n", style="white")
    body.append("Q  Quit\n\n", style="white")

    body.append("Analyze Input\n", style="bold cyan")
    body.append("- Paste or type your prompt (multi-line is fine).\n", style="white")
    body.append("- Press Enter on an empty line to submit.\n\n", style="white")

    body.append("Weak-Dimension Drill-Down Controls\n", style="bold cyan")
    body.append("n  Next weak area\n", style="white")
    body.append("p  Previous weak area\n", style="white")
    body.append("b  Back to menu\n\n", style="white")

    body.append("Navigation / Back Behavior\n", style="bold cyan")
    body.append("Use the main menu key you want (1, 2, 3, 4, H, or Q) at the prompt to move between screens.\n", style="white")
    body.append("If you finish a drill-down or analysis step, choose your next screen from the same menu prompt.\n\n", style="white")

    body.append("Best Prompt Checklist (Business Use)\n", style="bold cyan")
    body.append("[ ] Clear objective\n", style="white")
    body.append("[ ] Enough context\n", style="white")
    body.append("[ ] Explicit output format\n", style="white")
    body.append("[ ] Constraints (time, budget, policy, tone)\n", style="white")
    body.append("[ ] Success criteria\n", style="white")

    console.print(Panel(
        body,
        title="Help: Command Guide",
        border_style="white",
        padding=(1, 2),
    ))


# main loop, this is what keeps the whole thing running until the user quits

def main():
    current_screen = "welcome"

    while True:
        # redraw whichever screen were on
        console.clear()
        show_header()
        console.print()

        if current_screen == "analyze":
            result = screen_analyze()
            if result == "quit":
                console.clear()
                console.print("\n  [bold cyan]Goodbye![/bold cyan]\n")
                break
            current_screen = result
            continue
        elif current_screen == "history":
            screen_history()
        elif current_screen == "tips":
            screen_tips()
        elif current_screen == "team":
            screen_team()
        elif current_screen == "help":
            screen_help()
        else:
            screen_welcome()

        console.print()
        show_footer()
        console.print()
        show_menu()
        console.print()

        choice = input("  > ").strip().lower()

        # figure out where to go next based on what they typed
        # could probably use a dict for this but a bunch of elifs is easier to read
        if choice == "q" or choice == "quit":
            console.clear()
            console.print("\n  [bold cyan]Goodbye![/bold cyan]\n")
            break
        elif choice == "1":
            current_screen = "analyze"
        elif choice == "2":
            current_screen = "history"
        elif choice == "3":
            current_screen = "tips"
        elif choice == "4":
            current_screen = "team"
        elif choice == "h":
            current_screen = "help"
        # if they type anything weird I just reload the same screen so theres no crash


if __name__ == "__main__":
    main()
