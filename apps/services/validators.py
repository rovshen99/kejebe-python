
def validate_file_size(value):
    max_mb = 100
    if value.size > max_mb * 1024 * 1024:
        from django.core.exceptions import ValidationError
        raise ValidationError(f"File's weight more than {max_mb} MB.")
