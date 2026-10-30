from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("garden_planning", "0002_plant_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="status",
            field=models.CharField(
                choices=[
                    ("planning", "Perencanaan"),
                    ("ready", "Siap Tanam"),
                    ("planted", "Sudah Ditanam"),
                ],
                default="planning",
                max_length=20,
            ),
        ),
    ]
