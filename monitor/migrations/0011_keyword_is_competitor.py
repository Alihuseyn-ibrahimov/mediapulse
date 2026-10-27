from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0010_org_weekly_report'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyword',
            name='is_competitor',
            field=models.BooleanField(default=False, verbose_name='Rəqibdir'),
        ),
    ]
