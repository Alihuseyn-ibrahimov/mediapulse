from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0006_org_onboarding'),
    ]

    operations = [
        migrations.AddField(
            model_name='demorequest',
            name='plan',
            field=models.CharField(blank=True, max_length=100, verbose_name='Seçilmiş plan'),
        ),
    ]
