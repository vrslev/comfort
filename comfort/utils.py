import re


def parse_phone_number(phone):
    regex = re.compile(r"^((8|\+7)[\-– ]?)?(\(?\d{3}\)?[\-– ]?)?[\d\-– ]{7,10}$")
    if not re.match(regex, phone):
        return
    clean = re.sub(r"[^0-9]+", "", phone)
    if clean[:1] == "7":
        clean = "8" + clean[1:]
    return clean


def format_phone_number(phone):
    phone = parse_phone_number(phone)
    if not phone:
        return
    phone = "{} ({}) {}–{}–{}".format(
        phone[0], phone[1:4], phone[4:7], phone[7:9], phone[9:11]
    )
    return phone
