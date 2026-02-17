from datetime import datetime


def get_date_format():
    return '%d%b%Y'


def get_today_date():
    return datetime.now().strftime(get_date_format())
