from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0004_demorequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='notif_on_negative',
            field=models.BooleanField(default=True, verbose_name='Mənfi xəbərdə bildiriş'),
        ),
        migrations.AddField(
            model_name='organization',
            name='notif_on_positive',
            field=models.BooleanField(default=False, verbose_name='Müsbət xəbərdə bildiriş'),
        ),
        migrations.AddField(
            model_name='organization',
            name='notif_daily_summary',
            field=models.BooleanField(default=False, verbose_name='Gündəlik xülasə'),
        ),
        migrations.AddField(
            model_name='organization',
            name='notif_daily_hour',
            field=models.IntegerField(default=18, verbose_name='Xülasə saatı (0-23)'),
        ),
    ]
