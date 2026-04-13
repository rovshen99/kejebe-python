from django import forms

from apps.accounts.services.phone import normalize_phone


class DeleteAccountForm(forms.Form):
    phone = forms.CharField(max_length=32, label="Phone number")

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "")
        normalized = normalize_phone(raw)
        if not normalized:
            raise forms.ValidationError("Enter a valid phone number.")
        return normalized


class SupportRequestForm(forms.Form):
    name = forms.CharField(max_length=255, label="Your name", strip=True)
    phone = forms.CharField(max_length=32, label="Phone number")
    message = forms.CharField(
        label="How can we help?",
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 6}),
        strip=True,
    )

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "")
        normalized = normalize_phone(raw)
        if not normalized:
            raise forms.ValidationError("Enter a valid phone number.")
        return normalized
