from django.db import migrations

CREATE = """
CREATE OR REPLACE FUNCTION audit_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit log is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_auditentry
    FOR EACH ROW EXECUTE FUNCTION audit_append_only();
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_auditentry
    FOR EACH ROW EXECUTE FUNCTION audit_append_only();
"""

DROP = """
DROP TRIGGER IF EXISTS audit_no_update ON audit_auditentry;
DROP TRIGGER IF EXISTS audit_no_delete ON audit_auditentry;
DROP FUNCTION IF EXISTS audit_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]
    operations = [migrations.RunSQL(CREATE, DROP)]
