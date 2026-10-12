from django.conf import settings
from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage

def avatar_storage():
    return FileSystemStorage(location=settings.AVATAR_ROOT, base_url=settings.AVATAR_URL)
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    github_url = models.URLField(blank=True)
    tech_stack = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(storage=avatar_storage, upload_to="", blank=True)
    @property
    def tech_list(self):
        return [t.strip() for t in self.tech_stack.split(",") if t.strip()]
    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return settings.AVATAR_URL + "default.jpg"