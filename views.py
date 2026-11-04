from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from .models import Course, Submission


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
def exam(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    questions = list(course.questions.prefetch_related('choices'))
    if not questions:
        return HttpResponseBadRequest('This course has no exam.')

    fields = {f'question_{question.pk}' for question in questions}
    if any(key.startswith('question_') and key not in fields for key in request.POST):
        return HttpResponseBadRequest('The exam has changed. Reload the course page.')

    answers = []
    for question in questions:
        choices = list(question.choices.all())
        correct = [choice.text for choice in choices if choice.is_correct]
        if len(choices) < 2 or not correct:
            return HttpResponseBadRequest('This exam is not ready for submissions.')

        choices_by_id = {str(choice.pk): choice for choice in choices}
        selected_ids = set(request.POST.getlist(f'question_{question.pk}'))
        if not selected_ids.issubset(choices_by_id):
            return HttpResponseBadRequest('An answer does not belong to its question.')

        selected = [choice for key, choice in choices_by_id.items() if key in selected_ids]
        answers.append({
            'question': question.text,
            'selected': [choice.text for choice in selected],
            'correct': correct,
            'earned_point': len(selected) == len(correct) and all(
                choice.is_correct for choice in selected
            ),
        })

    submission = Submission.objects.create(course=course, user=request.user, answers=answers)
    return redirect('onlinecourse:show_exam_result', submission_id=submission.pk)


@require_safe
@login_required
def show_exam_result(request, submission_id):
    submission = get_object_or_404(
        Submission.objects.select_related('course'), pk=submission_id, user=request.user
    )
    return render(request, 'onlinecourse/exam_result.html', {
        'submission': submission,
        'score': sum(answer['earned_point'] for answer in submission.answers),
        'total': len(submission.answers),
    })
