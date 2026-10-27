from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0005_org_notif_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='onboarding_done',
            field=models.BooleanField(default=False, verbose_name='Onboarding tamamlandı'),
        ),
    ]
