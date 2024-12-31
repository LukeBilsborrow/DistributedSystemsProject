# Generated by Django 5.0.4 on 2024-04-18 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core_transcription', '0002_alter_transcriptionsubmission_date_submitted'),
    ]

    operations = [
        migrations.AddField(
            model_name='transcriptionsubmission',
            name='name',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='transcriptionsubmission',
            name='visibility',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.DeleteModel(
            name='Choice',
        ),
        migrations.DeleteModel(
            name='Question',
        ),
    ]
