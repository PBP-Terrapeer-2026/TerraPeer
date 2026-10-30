"""Keep old task links intact until the owner explicitly chooses an official plant."""

from django.db import migrations, models
import django.db.models.deletion


def rename_legacy_plant_index(apps, schema_editor):
    """RenameField keeps the old index name on PostgreSQL, so the new `plant` FK
    would try to create an index with the same name. Give the old one a new name."""
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'care_caretask' "
            "AND indexdef LIKE '%%(legacy_plant_id)%%'"
        )
        for (name,) in cursor.fetchall():
            if name.startswith("care_caretask_plant_id_"):
                schema_editor.execute(
                    f'ALTER INDEX "{name}" RENAME TO "care_caretask_legacy_plant_id_idx"'
                )


class Migration(migrations.Migration):
    dependencies = [
        ("care", "0002_protect_task_plant"),
        ("my_plants", "0004_daily_check_in_and_request_quota"),
        ("garden_setup", "0003_growingspace_other_space_type"),
    ]

    operations = [
        migrations.AlterModelTable(name="gardenspace", table="care_gardenspace"),
        migrations.RenameModel(old_name="GardenSpace", new_name="LegacyGardenSpace"),
        migrations.AlterModelOptions(
            name="legacygardenspace", options={"verbose_name": "Archived care space"}
        ),
        migrations.AlterModelTable(name="plant", table="care_plant"),
        migrations.RenameModel(old_name="Plant", new_name="LegacyPlant"),
        migrations.AlterModelOptions(
            name="legacyplant", options={"verbose_name": "Archived care plant"}
        ),
        migrations.RenameField(
            model_name="caretask", old_name="plant", new_name="legacy_plant"
        ),
        migrations.RunPython(rename_legacy_plant_index, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="caretask",
            name="legacy_plant",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="care_tasks",
                to="care.legacyplant",
            ),
        ),
        migrations.AddField(
            model_name="caretask",
            name="plant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="care_tasks",
                to="my_plants.plant",
            ),
        ),
        migrations.CreateModel(
            name="PlantCareSpace",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "plant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="care_location",
                        to="my_plants.plant",
                    ),
                ),
                (
                    "growing_space",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="care_locations",
                        to="garden_setup.growingspace",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="caretask",
            constraint=models.CheckConstraint(
                condition=models.Q(plant__isnull=False)
                | models.Q(legacy_plant__isnull=False),
                name="care_task_has_plant",
            ),
        ),
    ]
