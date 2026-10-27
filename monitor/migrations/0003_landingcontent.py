from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0002_keywordalias'),
    ]

    operations = [
        migrations.CreateModel(
            name='LandingContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Landing məzmunu',
                'verbose_name_plural': 'Landing məzmunu',
            },
        ),
    ]
