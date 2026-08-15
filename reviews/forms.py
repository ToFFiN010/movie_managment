from django import forms
from .models import Review, ReviewReport

class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} Stars") for i in range(5, 0, -1)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    review_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your experience, thoughts on plot, acting, visual effects...'})
    )

    class Meta:
        model = Review
        fields = ('rating', 'review_text')


class ReviewReportForm(forms.ModelForm):
    reason = forms.ChoiceField(
        choices=ReviewReport.Reason.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide additional details for moderation...'})
    )

    class Meta:
        model = ReviewReport
        fields = ('reason', 'description')
