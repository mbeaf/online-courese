from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .models import Course, Enrollment, Submission


@require_http_methods(['GET', 'POST'])
def register(request):
    next_url = request.POST.get('next') if request.method == 'POST' else request.GET.get('next')
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ''

    if request.user.is_authenticated:
        return redirect(next_url or 'onlinecourse:course_list')

    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect(next_url or 'onlinecourse:course_list')

    return render(request, 'registration/register.html', {'form': form, 'next': next_url})


@require_safe
def course_list(request):
    return render(request, 'onlinecourse/course_list.html', {'courses': Course.objects.all()})


@require_safe
def course_detail(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    questions = course.questions.prefetch_related('choices')
    return render(request, 'onlinecourse/course_details_bootstrap.html', {
        'course': course,
        'questions': questions,
    })


@require_POST
@login_required
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    questions = list(course.questions.prefetch_related('choices'))
    if not questions:
        return HttpResponseBadRequest('This course has no exam.')

    fields = {f'question_{question.pk}' for question in questions}
    if any(key.startswith('question_') and key not in fields for key in request.POST):
        return HttpResponseBadRequest('The exam has changed. Reload the course page.')

    answers = []
    selected_choices = []
    for question in questions:
        choices = list(question.choices.all())
        correct = [choice.choice_text for choice in choices if choice.is_correct]
        if len(choices) < 2 or not correct:
            return HttpResponseBadRequest('This exam is not ready for submissions.')

        choices_by_id = {str(choice.pk): choice for choice in choices}
        selected_ids = set(request.POST.getlist(f'question_{question.pk}'))
        if not selected_ids.issubset(choices_by_id):
            return HttpResponseBadRequest('An answer does not belong to its question.')

        selected = [choice for key, choice in choices_by_id.items() if key in selected_ids]
        selected_choices.extend(selected)
        answers.append({
            'question': question.text,
            'selected': [choice.choice_text for choice in selected],
            'correct': correct,
            'earned_point': question.is_get_score(choice.pk for choice in selected),
            'grade': question.grade,
        })

    with transaction.atomic():
        enrollment, _ = Enrollment.objects.get_or_create(course=course, user=request.user)
        submission = Submission.objects.create(enrollment=enrollment, answers=answers)
        submission.choices.set(selected_choices)
    return redirect('onlinecourse:show_exam_result', course_id=course.pk, submission_id=submission.pk)


@require_safe
@login_required
def show_exam_result(request, submission_id, course_id=None):
    submissions = Submission.objects.select_related('enrollment__course').filter(
        enrollment__user=request.user
    )
    if course_id is not None:
        submissions = submissions.filter(enrollment__course_id=course_id)
    submission = get_object_or_404(submissions, pk=submission_id)
    course = submission.enrollment.course
    if course_id is None:
        return redirect('onlinecourse:show_exam_result', course_id=course.pk, submission_id=submission.pk)

    grade = sum(answer.get('grade', 1) for answer in submission.answers if answer['earned_point'])
    return render(request, 'onlinecourse/exam_result.html', {
        'course': course,
        'submission': submission,
        'grade': grade,
        'score': grade,
        'selected_ids': list(submission.choices.values_list('pk', flat=True)),
        'total': sum(answer.get('grade', 1) for answer in submission.answers),
    })
