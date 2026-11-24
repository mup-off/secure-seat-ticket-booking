from datetime import timedelta

from django.db import migrations


def forwards(apps, schema_editor):
    """Events created before the draft/publish flow were 'active' (on sale) and had no
    end time. They become 'published', ending 3 hours after they start."""
    Event = apps.get_model("events", "Event")
    for event in Event.objects.filter(status="active"):
        event.status = "published"
        if event.starts_at and not event.ends_at:
            event.ends_at = event.starts_at + timedelta(hours=3)
        event.published_at = event.created_at
        event.save(update_fields=["status", "ends_at", "published_at"])


class Migration(migrations.Migration):
    dependencies = [("events", "0002_alter_tickettype_options_event_category_and_more")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
