from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Choice, Course, Question, Submission


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
    search_fields = ['title']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ['text', 'course']
    list_filter = ['course']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'course', 'user', 'submitted_at']
    readonly_fields = ['course', 'user', 'answers', 'submitted_at']

    def has_add_permission(self, request):
        return False
