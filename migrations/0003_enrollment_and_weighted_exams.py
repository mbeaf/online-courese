from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
from django.db.models import deletion


def backfill_enrollments(apps, schema_editor):
    db = schema_editor.connection.alias
    Enrollment = apps.get_model('onlinecourse', 'Enrollment')
    Question = apps.get_model('onlinecourse', 'Question')
    Submission = apps.get_model('onlinecourse', 'Submission')

    for submission in Submission.objects.using(db).iterator():
        enrollment, _ = Enrollment.objects.using(db).get_or_create(
            course_id=submission.course_id, user_id=submission.user_id
        )
        submission.enrollment_id = enrollment.pk
        submission.save(using=db, update_fields=['enrollment'])

        # Older attempts stored display text only. Link choices where the text is unambiguous.
        questions = {}
        for question in Question.objects.using(db).filter(
            course_id=submission.course_id
        ).prefetch_related('choices'):
            questions.setdefault(question.text, []).append(question)
        selected_ids = []
        for answer in submission.answers:
            matches = questions.get(answer['question'], [])
            if len(matches) != 1:
                continue
            choices = {}
            for choice in matches[0].choices.all():
                choices.setdefault(choice.choice_text, []).append(choice.pk)
            for text in answer['selected']:
                ids = choices.get(text, [])
                if len(ids) == 1:
                    selected_ids.append(ids[0])
        submission.choices.set(selected_ids)


class Migration(migrations.Migration):
    dependencies = [
        ('onlinecourse', '0002_lesson'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(model_name='choice', old_name='text', new_name='choice_text'),
        migrations.AddField(
            model_name='question', name='grade',
            field=models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)]),
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course', models.ForeignKey(on_delete=deletion.CASCADE, related_name='enrollments', to='onlinecourse.course')),
                ('user', models.ForeignKey(on_delete=deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'constraints': [
                models.UniqueConstraint(fields=('course', 'user'), name='unique_course_enrollment'),
            ]},
        ),
        migrations.AddField(
            model_name='submission', name='enrollment',
            field=models.ForeignKey(null=True, on_delete=deletion.CASCADE, related_name='submissions', to='onlinecourse.enrollment'),
        ),
        migrations.AddField(
            model_name='submission', name='choices',
            field=models.ManyToManyField(blank=True, to='onlinecourse.choice'),
        ),
        migrations.RunPython(backfill_enrollments),
        migrations.AlterField(
            model_name='submission', name='enrollment',
            field=models.ForeignKey(on_delete=deletion.CASCADE, related_name='submissions', to='onlinecourse.enrollment'),
        ),
        migrations.RemoveField(model_name='submission', name='course'),
        migrations.RemoveField(model_name='submission', name='user'),
    ]
