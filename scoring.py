# just the letter grade logic, I split this out so it wasnt cluttering my main file


def letter_grade(score):
    """turns a number score into a letter grade, same scale my school uses"""
    # I could probably do this with a dict and a loop but ifs are easier to read
    if score >= 97:
        return "A+"
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 67:
        return "D+"
    if score >= 63:
        return "D"
    if score >= 60:
        return "D-"
    # anything under 60 is an F, no minuses or pluses on F
    return "F"
