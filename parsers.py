import re

def parse_history_bowl(text):
    # Remove page numbers and their preceding line
    clean_text = re.sub(r"[^\n]*\n\d+\n\n", "", text)

    # Parse first quarter
    q1_text = re.search(r"(?s)<b>First Quarter(\s*)</b>\n(.*?)(?=\n+<b>Second Quarter(\s*)</b>)", clean_text).group()
    q1_questions = re.findall(r"\((\d+)\)\s*(.*?)\nANSWER:\s*(.+?)(?=\n\(\d+|\Z)", q1_text, re.MULTILINE | re.DOTALL)

    q1_questions_parsed = [
        {
            "number": question[0],
            "question_text": question[1],
            "answer": question[2],
        } for question in q1_questions
    ]

    # Parse second quarter
    q2_text = re.search(r"(?s)<b>Second Quarter(\s*)</b>\n(.*?)(?=\n+<b>Third Quarter(\s*)</b>)", clean_text).group()
    q2_questions = re.findall(r"\((\d+)\)\s*(.*?)\nANSWER:\s*(.+?)(?:\nBONUS:\s*(.*?)\nANSWER:\s*(.+?))?(?=\n\(\d+|\Z)", q2_text, re.MULTILINE | re.DOTALL)

    q2_questions_parsed = [
        {
            "number": question[0],
            "question_text": question[1],
            "answer": question[2],
            "bonus_text": question[3],
            "bonus_answer": question[4],
        } for question in q2_questions
    ]

    # Parse third quarter
    q3_text = re.search(r"(?s)<b>Third Quarter(\s*)</b>\n(.*?)(?=\n+<b>Fourth Quarter(\s*)</b>)", clean_text).group()
    q3_categories = re.findall(r" \d\. (.*?)\n", q3_text, re.MULTILINE | re.DOTALL)
    q3_titles_leadins = re.findall(r"<i><b>(.*?)(?=\s*)</b></i>\n(.*?\.{3})\n", q3_text, re.MULTILINE)
    q3_questions = re.findall(r"\((\d+)\)\s*(.*?)\nANSWER:\s*(.+?)(?=\n\(\d+|\Z|(?=<i><b>(.*?)(?=\s*)</b></i>\n(.*?\.{3})\n))", q3_text, re.MULTILINE | re.DOTALL)
    q3_count = len(q3_questions) // 3
    q3_questions = [q3_questions[:q3_count], q3_questions[q3_count:2*q3_count], q3_questions[2*q3_count:]]

    q3_questions_parsed = [[], [], []]
    for category, questions in enumerate(q3_questions):
        for question in questions:
            q3_questions_parsed[category].append({
                "number": question[0],
                "question_text": question[1],
                "answer": question[2].strip(),
            })

    q3_parsed = {}
    for i in range(3):
        q3_parsed["category_" + str(i + 1)] = {
            "topic": q3_categories[i],
            "title": q3_titles_leadins[i][0],
            "lead_in": q3_titles_leadins[i][1],
            "questions": q3_questions_parsed[i],
        }

    # Parse fourth quarter
    q4_text = re.search(r"(?s)<b>Fourth Quarter(\s*)</b>\n(.*?)(?=\n+<b>Extra Questions(\s*)</b>)", clean_text).group()
    q4_questions = re.findall(r"\((\d+)\)\s*(.*?)\nANSWER:\s*(.+?)(?=\n\(\d+|\Z)", q4_text, re.MULTILINE | re.DOTALL)

    q4_questions_parsed = [
        {
            "number": question[0],
            "question_text": question[1],
            "answer": question[2],
        } for question in q4_questions
    ]

    # Parse extra questions
    eq_text = re.search(r"(?s)<b>Extra Questions(\s*)</b>\n(.*?)$", clean_text).group()
    tiebreaker = re.search(r"\([\w ]+\)\s*(.*?)\nANSWER:\s*(.+?)(?=\n\(\d+|\Z)", eq_text, re.MULTILINE | re.DOTALL)
    tiebreaker_parsed = {
        "question_text": tiebreaker.group(1),
        "answer": tiebreaker.group(2),
    }
    extra_question = re.search(r"\(\d+\)\s*(.*?)\nANSWER:\s*(.+?)(?:\nBONUS:\s*(.*?)\nANSWER:\s*(.+?))?(?=\n\(\d+|\Z)", eq_text, re.MULTILINE | re.DOTALL)
    extra_tossup_parsed = {
        "question_text": extra_question.group(1),
        "answer": extra_question.group(2),
    }
    extra_bonus_parsed = {
        "bonus_text": extra_question.group(3),
        "bonus_answer": extra_question.group(4),
    }

    return {
        "first_quarter": q1_questions_parsed,
        "second_quarter": q2_questions_parsed,
        "third_quarter": q3_parsed,
        "fourth_quarter": q4_questions_parsed,
        "extra_questions": {
            "tiebreaker": tiebreaker_parsed,
            "extra_tossup": extra_tossup_parsed,
            "extra_bonus": extra_bonus_parsed
        }
    }