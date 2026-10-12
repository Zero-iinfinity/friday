from django import forms
from django.contrib.auth import get_user_model
from .models import Profile


class UserNamesForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["bio", "avatar", "github_url", "tech_stack"]

    def clean_avatar(self):
        f = self.cleaned_data.get("avatar")
        if f and hasattr(f, "size") and f.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image under 3 MB.")
        return f