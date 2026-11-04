from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Choice, Course, Lesson, Question, Submission


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ['text', 'grade']
    readonly_fields = ['text', 'grade']
    show_change_link = True
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


class ChoiceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active = [
            form.cleaned_data for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE')
        ]
        if len(active) < 2 or not any(choice['is_correct'] for choice in active):
            raise ValidationError('Add at least two choices and mark at least one correct.')


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceFormSet
    extra = 2


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    search_fields = ['title']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'position']
    list_filter = ['course']
    search_fields = ['title', 'course__title']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ['text', 'course', 'grade']
    list_filter = ['course']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enrollment', 'submitted_at']
    readonly_fields = ['enrollment', 'choices', 'answers', 'submitted_at']

    def has_add_permission(self, request):
        return False
