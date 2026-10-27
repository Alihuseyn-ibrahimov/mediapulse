from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0009_landingcontent_lang'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='weekly_report_enabled',
            field=models.BooleanField(default=False, verbose_name='Həftəlik PDF hesabat'),
        ),
        migrations.AddField(
            model_name='organization',
            name='report_email',
            field=models.EmailField(blank=True, verbose_name='Hesabat e-poçtu'),
        ),
    ]
