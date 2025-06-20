import os
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def random_bg_image():
    img_dir = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'img')
    try:
        files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))]
    except Exception:
        files = []
    import random
    if files:
        return 'img/' + random.choice(files)
    return ''
