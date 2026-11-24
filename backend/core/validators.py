"""Server-side input checks (plan, Phase 3: Input validation). Checks in the React app
are only for convenience; these are the ones that count."""
import re

from rest_framework import serializers

RW_MOBILE = re.compile(r"^(?:\+?250|0)?(7[2389]\d{7})$")


def normalize_rw_phone(value):
    """MTN (078, 079) and Airtel (072, 073) Rwanda numbers -> 2507XXXXXXXX."""
    m = RW_MOBILE.match(re.sub(r"[\s-]", "", str(value)))
    if not m:
        raise serializers.ValidationError("Enter a valid MTN or Airtel Rwanda number, e.g. 0788123456.")
    return "250" + m.group(1)


class StrictSerializer(serializers.Serializer):
    """Rejects any field the serializer does not declare.

    This is how checkout refuses a price from the client: "price", "total",
    "amount" and anything else not on the list make the whole request invalid.
    """

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"detail": "Expected a JSON object."})
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({"unexpected_fields": unknown})
        return super().to_internal_value(data)
