"""Context processors ของแอป accounts"""

# url_name -> เมนูใน navbar ที่ต้องไฮไลต์
_SECTION_BY_URL_NAME = {
    "find_match": "match",
    "create_project": "match",
    "profile_detail": "profile",
    "edit_profile": "profile",
    "login": "login",
    "register": "register",
}

# namespace ของแอป -> เมนูใน navbar
_SECTION_BY_NAMESPACE = {
    "board": "board",
    "chat": "chat",
}


def nav_section(request):
    """บอก navbar ว่าตอนนี้อยู่หน้าไหน (ใช้ไฮไลต์เมนู) เช่น "board", "chat", "match"""
    match = getattr(request, "resolver_match", None)
    if match is None:
        return {"nav_section": ""}
    section = _SECTION_BY_NAMESPACE.get(match.namespace) or _SECTION_BY_URL_NAME.get(
        match.url_name, ""
    )
    return {"nav_section": section}
