from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_alter_messagevote_user'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', '-time'], name='chat_message_room_time_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', 'time'], name='chat_message_room_time_asc_idx'),
        ),
        migrations.AddIndex(
            model_name='messagevote',
            index=models.Index(fields=['message', 'vote'], name='chat_messagevote_msg_vote_idx'),
        ),
        migrations.AddIndex(
            model_name='messageattachment',
            index=models.Index(fields=['message'], name='chat_messageattachment_msg_idx'),
        ),
    ]
