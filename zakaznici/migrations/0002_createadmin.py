from django.db import migrations

def create_superuser(apps, schema_editor):
    # Načteme standardní Django User model
    User = apps.get_model('auth', 'User')
    
    # Vytvoříme superusera, pokud neexistuje
    if not User.objects.filter(username='admin').exists():
        print("Nový superuser 'admin' / '1234' vytvořen")
        User.objects.create_superuser(
            username='admin',
            email='',
            password='1234'
        )

def remove_superuser(apps, schema_editor):
    # Funkce pro rollback - smaže superusera 'admin'
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='admin').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('zakaznici', '0001_initial'), 
    ]

    operations = [
        migrations.RunPython(create_superuser, remove_superuser),
    ]