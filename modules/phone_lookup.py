import phonenumbers
from phonenumbers import geocoder, carrier, timezone


def parse_phone(number: str) -> dict:
    try:
        parsed = phonenumbers.parse(number, None)
    except phonenumbers.NumberParseException as e:
        return {"error": str(e)}

    valid = phonenumbers.is_valid_number(parsed)
    possible = phonenumbers.is_possible_number(parsed)

    result = {
        "valid": valid,
        "possible": possible,
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "country_code": str(parsed.country_code),
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "region": geocoder.description_for_number(parsed, "ru"),
        "carrier": carrier.name_for_number(parsed, "ru"),
        "timezones": list(timezone.time_zones_for_number(parsed)),
        "number_type": _number_type(parsed),
    }
    return result


def _number_type(parsed) -> str:
    t = phonenumbers.number_type(parsed)
    types = {
        phonenumbers.PhoneNumberType.MOBILE: "Мобильный",
        phonenumbers.PhoneNumberType.FIXED_LINE: "Стационарный",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Стационарный/Мобильный",
        phonenumbers.PhoneNumberType.TOLL_FREE: "Бесплатный (0-800)",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "Премиум",
        phonenumbers.PhoneNumberType.VOIP: "VoIP",
        phonenumbers.PhoneNumberType.PAGER: "Пейджер",
        phonenumbers.PhoneNumberType.UNKNOWN: "Неизвестно",
    }
    return types.get(t, "Неизвестно")
