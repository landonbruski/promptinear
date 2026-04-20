# tiny helper file, originally had more in here but I moved most of it into promptinear.py


def weakest_dimension(averages):
    """finds the dimension with the lowest score so I can tell the user where they need the most work"""
    # pretty sure theres a one liner with min() but I wanted to do it myself to understand it
    if not averages:
        raise ValueError("averages dict is empty")

    lowest_name = None
    lowest_score = None
    for name in averages:
        score = averages[name]
        # first time through lowest_score is None so I always replace it
        if lowest_score is None or score < lowest_score:
            lowest_name = name
            lowest_score = score
    return (lowest_name, lowest_score)
