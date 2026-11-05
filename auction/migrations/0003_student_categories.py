"""Initial student study-area categories (idempotent data migration)."""
from django.db import migrations

STUDY_AREAS = [
    "Информатика и программирование",
    "Искусственный интеллект и анализ данных",
    "Информационная безопасность",
    "Математика и прикладная математика",
    "Физика и астрономия",
    "Химия и материаловедение",
    "Биология и биотехнологии",
    "Медицина и здравоохранение",
    "Экономика и финансы",
    "Менеджмент и предпринимательство",
    "Юриспруденция",
    "Психология",
    "Педагогика и образование",
    "Лингвистика и перевод",
    "История и археология",
    "Филология и журналистика",
    "Дизайн и цифровое искусство",
    "Архитектура и строительство",
    "Машиностроение и робототехника",
    "Электроника и телекоммуникации",
    "Экология и природопользование",
    "Социология и политология",
    "Маркетинг и реклама",
    "Туризм и гостиничное дело",
]


def populate_study_areas(apps, schema_editor):
    Category = apps.get_model("auction", "Category")
    db = schema_editor.connection.alias
    for name in STUDY_AREAS:
        Category.objects.using(db).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("auction", "0002_auctionrequest")]
    operations = [migrations.RunPython(populate_study_areas, migrations.RunPython.noop)]
