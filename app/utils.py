import unicodedata

def normalize_apostrophes(text):
    """
    Normalize all types of apostrophes in a string to the standard ASCII apostrophe (U+0027).
    This handles various Unicode apostrophes, quotes, and similar characters.
    """
    if not text:
        return text
        
    # List of characters to normalize to standard apostrophe
    apostrophe_chars = {
        '\u2018',  # LEFT SINGLE QUOTATION MARK
        '\u2019',  # RIGHT SINGLE QUOTATION MARK
        '\u201B',  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
        '\u2032',  # PRIME
        '\u0060',  # GRAVE ACCENT
        '\u00B4',  # ACUTE ACCENT
        '\u2035',  # REVERSED PRIME
        '\u275B',  # HEAVY SINGLE TURNED COMMA QUOTATION MARK ORNAMENT
        '\u275C',  # HEAVY SINGLE COMMA QUOTATION MARK ORNAMENT
        '\uFF07',  # FULLWIDTH APOSTROPHE
    }
    
    # First normalize using NFKC to handle composite characters
    text = unicodedata.normalize('NFKC', text)
    
    # Then replace all apostrophe-like characters with standard ASCII apostrophe
    for char in apostrophe_chars:
        text = text.replace(char, "'")
    
    return text

def normalize_team_name(name):
    """
    Normalize a team name by handling apostrophes and other special characters.
    This should be used whenever storing or comparing team names.
    """
    if not name:
        return name
    return normalize_apostrophes(name.strip()) 