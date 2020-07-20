def canonical_uuid(uuid):
    """
    formats to uuid 8-4-4-8
    """
    if "-" not in uuid:
        return f"{ uuid[0:8] }-{ uuid[8:12] }-{ uuid[12:16] }-{ uuid[16:] }"
    return uuid
