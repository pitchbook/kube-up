def timestr_to_seconds(timestr: str) -> int:
    """
    Convert a Kubernetes time string to seconds

    :param timestr: time string
    :return: seconds
    """

    if timestr.endswith("m"):
        seconds = float(timestr.rstrip("m")) * 60
    elif timestr.endswith("s"):
        seconds = float(timestr.rstrip("s"))
    elif timestr.endswith("h"):
        seconds = float(timestr.rstrip("h")) * 60 * 60
    else:
        raise ValueError(f"Unsupported time string '{timestr}'")

    return int(seconds)


def timestr_to_minutes(timestr: str) -> str:
    """
    Convert a Kubernetes time string to minutes

    :param timestr: time string
    :return: minutes
    """

    return str(timestr_to_seconds(timestr) // 60)
