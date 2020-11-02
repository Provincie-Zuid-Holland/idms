def mimetype2FileType(mimetype: str) -> str:
    """
    Lookup table for mime type to file type.
    """
    convertDict = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel"
    }
    return convertDict.get(mimetype, "Mimetype not Found: " + str(mimetype))