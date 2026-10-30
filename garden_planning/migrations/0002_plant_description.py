from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("garden_planning", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plant",
            name="description",
            field=models.TextField(blank=True),
        ),
    ]
