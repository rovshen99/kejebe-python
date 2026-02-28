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
