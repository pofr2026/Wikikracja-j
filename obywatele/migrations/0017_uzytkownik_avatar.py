from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('obywatele', '0016_uzytkownik_email_notifications_chat_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='uzytkownik',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='Avatar'),
        ),
    ]
