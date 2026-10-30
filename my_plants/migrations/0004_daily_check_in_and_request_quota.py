import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def preserve_check_in_history(apps, schema_editor):
    CheckIn = apps.get_model('my_plants', 'PlantCheckIn')
    seen = set()
    for check_in in CheckIn.objects.using(schema_editor.connection.alias).order_by('-created_at', '-pk').iterator():
        day = django.utils.timezone.localtime(check_in.created_at).date()
        key = (check_in.plant_id, day)
        if key not in seen:
            CheckIn.objects.using(schema_editor.connection.alias).filter(pk=check_in.pk).update(checked_on=day)
            seen.add(key)


class Migration(migrations.Migration):
    dependencies = [
        ('my_plants', '0003_plantphoto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name='plantcheckin', name='checked_on', field=models.DateField(editable=False, null=True)),
        migrations.RunPython(preserve_check_in_history, migrations.RunPython.noop),
        migrations.AlterField(model_name='plantcheckin', name='checked_on', field=models.DateField(default=django.utils.timezone.localdate, editable=False, null=True)),
        migrations.AddConstraint(model_name='plantcheckin', constraint=models.UniqueConstraint(fields=('plant', 'checked_on'), name='my_plants_one_daily_check_in')),
        migrations.CreateModel(name='RequestQuota', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('scope', models.CharField(max_length=32)),
            ('window', models.BigIntegerField(default=0)),
            ('hits', models.PositiveIntegerField(default=0)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'constraints': [models.UniqueConstraint(fields=('user', 'scope'), name='my_plants_unique_request_quota')]}),
        migrations.AddIndex(model_name='plant', index=models.Index(fields=['owner', 'planted_on'], name='mp_owner_planted_idx')),
        migrations.AddIndex(model_name='plantcheckin', index=models.Index(fields=['plant', '-created_at', '-id'], name='mp_check_latest_idx')),
        migrations.AddIndex(model_name='plantphoto', index=models.Index(fields=['plant', '-created_at', '-id'], name='mp_photo_latest_idx')),
    ]
