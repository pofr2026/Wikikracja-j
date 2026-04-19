from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('obywatele', '0017_uzytkownik_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzytkownik',
            name='language',
            field=models.CharField(
                blank=True,
                default='',
                max_length=10,
                verbose_name='Language',
            ),
        ),
    ]
