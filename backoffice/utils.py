def breakdown_timedelta(timedelta):
    if timedelta is None:
        return None
    seconds_in_an_hour = 60 * 60
    seconds_in_a_day = 24 * seconds_in_an_hour
    seconds_in_a_month = 30 * seconds_in_a_day
    seconds_in_a_year = 365 * seconds_in_a_day

    all_seconds = timedelta.days * seconds_in_a_day + timedelta.seconds
    years, seconds_remaining = divmod(all_seconds, seconds_in_a_year)
    months, seconds_remaining = divmod(seconds_remaining, seconds_in_a_month)
    days, seconds_remaining = divmod(seconds_remaining, seconds_in_a_day)
    hours, seconds_remaining = divmod(seconds_remaining, seconds_in_an_hour)
    minutes, seconds_remaining = divmod(seconds_remaining, 60)
    seconds = int(seconds_remaining)
    if years > 0:
        years_str = f"{years} years, "
    else:
        years_str = ""
    if months > 0:
        months_str = f"{months} months, "
    else:
        months_str = ""
    if days > 0:
        days_str = f"{days} days, "
    else:
        days_str = ""
    if hours > 0:
        hours_str = f"{hours} hours, "
    else:
        hours_str = ""
    if minutes > 0:
        minutes_str = f"{minutes} minutes, "
    else:
        minutes_str = ""
    if seconds > 0:
        seconds_str = f"and {seconds} seconds"
    else:
        seconds_str = ""

    return f"{years_str}{months_str}{days_str}{hours_str}{minutes_str}{seconds_str}"
