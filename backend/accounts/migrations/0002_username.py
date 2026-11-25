import re

from django.db import migrations, models
from django.db.models.functions import Lower

import accounts.models


def fill_usernames(apps, schema_editor):
    """Existing accounts get a username made from their email name (e.g.
    jean.paul@x.com -> jean.paul), with a number added if it is already taken."""
    User = apps.get_model("accounts", "User")
    taken = set()
    for user in User.objects.order_by("id"):
        base = re.sub(r"[^a-z0-9._-]", "", user.email.split("@")[0].lower())[:24] or "user"
        if not base[0].isalnum():
            base = "u" + base
        base = base.ljust(3, "0")
        if base in accounts.models.RESERVED_USERNAMES:
            base = f"{base}-user"
        name, n = base, 1
        while name in taken:
            n += 1
            name = f"{base}{n}"
        taken.add(name)
        user.username = name
        user.save(update_fields=["username"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="user", name="username", field=models.CharField(max_length=30, null=True)),
        migrations.RunPython(fill_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user", name="username",
            field=models.CharField(max_length=30, unique=True, validators=[accounts.models.validate_username])),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(condition=models.Q(username=Lower("username")), name="username_lowercase")),
    ]
