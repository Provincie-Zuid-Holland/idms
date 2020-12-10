# from mimetype_description import get_mime_type_description

def mimetype2FileType(mimetype: str) -> str:
    """
    Lookup table for mime type to file type.
    """
    convertDict = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
        "application/x-zip-compressed": "Compressed folder",
        "application/x-outlook-msg": "Mail message",
        "application/octet-stream": "Data file (csv?)"
    }
    return convertDict.get(mimetype) or "Mimetype not Found: " + str(mimetype) # or get_mime_type_description(mimetype) 