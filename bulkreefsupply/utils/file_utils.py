import os
from csv import DictReader


def get_csv_records(filepath):
    if not os.path.exists(filepath):
        return []
    return [dict(r) for r in DictReader(open(filepath, encoding='utf-8')) if r]
