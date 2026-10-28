from django.db import migrations


def add_email_pages(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    for pagina in ('email', 'email_legacy', 'email_list', 'email_detail'):
        cursor.execute('SELECT 1 FROM lstPagina WHERE pagina = %s LIMIT 1', [pagina])
        if cursor.fetchone() is None:
            cursor.execute('INSERT INTO lstPagina (pagina) VALUES (%s)', [pagina])


def remove_email_pages(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute(
        'DELETE FROM lstPagina WHERE pagina IN (%s, %s, %s, %s)',
        ('email', 'email_legacy', 'email_list', 'email_detail'),
    )


class Migration(migrations.Migration):
    dependencies = [('email', '0001_initial')]
    operations = [migrations.RunPython(add_email_pages, remove_email_pages)]
