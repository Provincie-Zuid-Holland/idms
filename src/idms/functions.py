from mimetype_description import get_mime_type_description

def mimetype2FileType(mimetype: str) -> str:
    """
    Lookup table for mime type to file type.
    """
    return get_mime_type_description(mimetype) or "Mimetype not Found: " + str(mimetype)