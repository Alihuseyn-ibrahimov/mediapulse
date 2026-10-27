from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0007_demorequest_plan'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', 'Əlavə edildi'), ('UPDATE', 'Dəyişdirildi'), ('DELETE', 'Silindi'), ('ACTION', 'Əməliyyat')], max_length=10, verbose_name='Əməliyyat')),
                ('model_name', models.CharField(max_length=100, verbose_name='Model')),
                ('object_id', models.CharField(blank=True, max_length=50, verbose_name='Obyekt ID')),
                ('object_repr', models.CharField(blank=True, max_length=500, verbose_name='Obyekt')),
                ('changes', models.TextField(blank=True, verbose_name='Dəyişikliklər')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP ünvan')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Tarix')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='İstifadəçi')),
            ],
            options={
                'verbose_name': 'Audit qeydi',
                'verbose_name_plural': 'Audit arxivi',
                'ordering': ['-timestamp'],
            },
        ),
    ]
