from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0003_landingcontent'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemoRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Ad Soyad')),
                ('company', models.CharField(max_length=200, verbose_name='Şirkət/Qurum adı')),
                ('contact', models.CharField(max_length=200, verbose_name='Telefon / E-poçt')),
                ('message', models.TextField(blank=True, verbose_name='Qeyd')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Tarix')),
                ('is_read', models.BooleanField(default=False, verbose_name='Baxılıb')),
            ],
            options={
                'verbose_name': 'Demo müraciəti',
                'verbose_name_plural': 'Demo müraciətləri',
                'ordering': ['-created_at'],
            },
        ),
    ]
