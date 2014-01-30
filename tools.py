
def get_date_lower(year, month, interval):
    year, month = divmod(int((year * 12 + month - 1) / interval) * interval, 12)
    return (year, month + 1)

def get_date_upper(year, month, interval):
    year, month = divmod(int((year * 12 + month + interval - 1) / interval) * interval, 12)
    return (year, month + 1)

