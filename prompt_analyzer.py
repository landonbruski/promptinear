# this is the file that actually grades the prompts
# originally I wanted to use the Gemini API here so I could have real AI grade the prompt
# I got it kinda working but it kept timing out and I didn't want the app to break
# for anyone who didnt have an api key, so I ended up just doing it myself with my own rules
# maybe someday I'll come back and add it as an optional thing

DIMS = ["clarity", "context", "structure", "actionability", "efficiency", "grounding"]


class PromptAnalyzer:
    """this is my class for grading prompts on the 6 things I decided matter"""

    def __init__(self):
        # I keep the last reasons here in case I want to show them later
        self.last_reasons = {}

    def analyze(self, message):
        # honestly this function used to be way longer when I had gemini in it
        text = message.content
        scores = fallback_scores(text)
        self.last_reasons = fallback_reasons(text)
        return build_result(scores)


def build_result(scores):
    """I just pack the scores into the shape my main file is expecting"""
    result = {}
    total = 0.0
    for dim in DIMS:
        result[dim] = float(scores[dim])
        total = total + float(scores[dim])
    # grade is just the average of the 6 dimensions, nothing fancy
    result["grade"] = round(total / len(DIMS), 1)
    return result


def keep_in_range(value):
    # quick helper so my scores never end up above 100 or below 0
    # I was getting weird negative numbers before I added this
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


# these are the filler words I look for
# there's probably more I could add but these are the ones I noticed myself using a lot
FILLER_PHRASES = ["please", "thanks", "could you", "would you mind", "i was wondering"]


def count_filler(text):
    # I just lowercase the text first so "Please" and "please" both count
    lower = text.lower()
    hits = 0
    for phrase in FILLER_PHRASES:
        if phrase in lower:
            hits = hits + 1
    return hits


def has_file_path(text):
    # pretty basic check, if a word has a / AND a . I assume its a file path
    # not perfect but it works for stuff like data/parser.py
    for word in text.split():
        if "/" in word and "." in word:
            return True
    return False


def fallback_scores(text):
    # this is the main scoring function, took me a while to get the numbers to feel right
    words = text.split()
    word_count = len(words)
    filler_hits = count_filler(text)
    file_found = has_file_path(text)
    has_code = "```" in text
    has_lines = "\n" in text.strip()

    # I tried a bunch of word count ranges, this is what felt fair to me
    # really short prompts are usually bad, really long ones are usually bloated
    if word_count < 5:
        base = 30
    elif word_count < 15:
        base = 55
    elif word_count < 60:
        base = 70
    elif word_count < 120:
        base = 60
    else:
        base = 45

    clarity = base

    context = base
    if word_count >= 20:
        # if they wrote enough words theres probably some context in there
        context = base + 10

    structure = base
    if has_lines or has_code:
        # multiline or code block means they structured it a bit
        structure = base + 15

    actionability = base

    # efficiency starts at 80 and gets docked for filler
    efficiency = 80 - filler_hits * 15
    if word_count > 150:
        efficiency = efficiency - 15

    # grounding is all about whether they referenced real things
    grounding = 30
    if file_found:
        grounding = grounding + 30
    if has_code:
        grounding = grounding + 25

    result = {}
    result["clarity"] = keep_in_range(clarity)
    result["context"] = keep_in_range(context)
    result["structure"] = keep_in_range(structure)
    result["actionability"] = keep_in_range(actionability)
    result["efficiency"] = keep_in_range(efficiency)
    result["grounding"] = keep_in_range(grounding)
    return result


def fallback_reasons(text):
    # I also wanted to show a little reason next to each score so its not just a number
    word_count = len(text.split())
    file_found = has_file_path(text)
    has_code = "```" in text
    filler_hits = count_filler(text)

    if has_code:
        structure = "Has code block."
    elif "\n" in text:
        structure = "Multi-line prompt."
    else:
        structure = "Single line, no formatting."

    if file_found:
        grounding = "File path found."
    elif has_code:
        grounding = "Code block found."
    else:
        grounding = "No file path or code block."

    if filler_hits > 0:
        efficiency = f"Filler phrases: {filler_hits}."
    else:
        efficiency = "No filler phrases detected."

    reasons = {}
    reasons["clarity"] = f"Heuristic from word count: {word_count}."
    reasons["context"] = "Heuristic; no semantic check available."
    reasons["structure"] = structure
    reasons["actionability"] = "Heuristic; verb detection disabled."
    reasons["efficiency"] = efficiency
    reasons["grounding"] = grounding
    return reasons
