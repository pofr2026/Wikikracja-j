from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('obywatele', '0011_remove_duplicate_emails'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
