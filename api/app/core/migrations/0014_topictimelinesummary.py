# Generated manually to match core.models.TopicTimelineSummary

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_pushsubscription'),
    ]

    operations = [
        migrations.CreateModel(
            name='TopicTimelineSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('generated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('model_name', models.CharField(blank=True, max_length=120)),
                ('entries', models.JSONField(blank=True, default=list)),
                ('topic', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_summary', to='core.searchtopic')),
            ],
        ),
    ]
