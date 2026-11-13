from datetime import date


def calculate_age(birth_date: date) -> int:
    today = date.today()
    before_birthday = (today.month, today.day) < (birth_date.month, birth_date.day)
    return today.year - birth_date.year - before_birthday