from django.db import models
from django.utils.text import slugify


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    summary = models.TextField(help_text="A short summary of the blog post")
    content = models.TextField()
    published_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords for SEO")

    class Meta:
        ordering = ['-published_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
