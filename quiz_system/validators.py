from datetime import datetime


def now_local():
    """Current time in server local timezone (matches browser datetime-local)."""
    return datetime.now()


def normalize_datetime_str(value):
    """Store quiz times as YYYY-MM-DD HH:MM:SS in local time."""
    if not value:
        return value
    dt, err = parse_datetime(value)
    if err or not dt:
        return value
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(value):
    if not value:
        return None, "Datetime is required."
    cleaned = str(value).strip().replace("Z", "").replace("T", " ")
    if len(cleaned) == 16:
        cleaned += ":00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(cleaned, fmt), None
        except ValueError:
            continue
    return None, "Invalid datetime format."


def validate_email(email):
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return None, "Valid email is required."
    return email, None


def validate_quiz_times(start_str, end_str):
    start, err = parse_datetime(start_str)
    if err:
        return None, None, err
    end, err = parse_datetime(end_str)
    if err:
        return None, None, err
    if start >= end:
        return None, None, "Quiz start time must be earlier than end time."
    return start, end, None


def validate_questions(questions):
    if not questions:
        return "At least one question is required."
    for i, q in enumerate(questions):
        stmt = (q.get("statement") or "").strip()
        if not stmt:
            return f"Question {i + 1}: statement cannot be empty."
        options = q.get("options") or []
        if len(options) < 2:
            return f"Question {i + 1}: at least 2 options required."
        texts = []
        correct = None
        for j, opt in enumerate(options):
            text = (opt.get("text") or opt.get("option_text") or "").strip()
            if not text:
                return f"Question {i + 1}, option {j + 1}: text cannot be empty."
            texts.append(text)
            if opt.get("is_correct"):
                correct = text
        if not correct:
            return f"Question {i + 1}: mark one correct answer."
        if correct not in texts:
            return f"Question {i + 1}: correct answer must match a provided option."
    return None


def quiz_is_active(start_iso, end_iso, now=None):
    now = now or now_local()
    start, _ = parse_datetime(start_iso)
    end, _ = parse_datetime(end_iso)
    if not start or not end:
        return False
    return start <= now <= end


def quiz_not_started(start_iso, now=None):
    now = now or now_local()
    start, _ = parse_datetime(start_iso)
    return start and now < start


def quiz_ended(end_iso, now=None):
    now = now or now_local()
    end, _ = parse_datetime(end_iso)
    return end and now > end
