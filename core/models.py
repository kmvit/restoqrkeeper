from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Page(models.Model):
    title = models.CharField(_('Заголовок'), max_length=200)
    slug = models.SlugField(_('URL-путь'), max_length=200, unique=True)
    content = models.TextField(_('Содержимое'))
    is_published = models.BooleanField(_('Опубликовано'), default=True)
    show_in_menu = models.BooleanField(_('Показывать в меню'), default=False)
    order = models.IntegerField(_('Порядок'), default=0)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Страница')
        verbose_name_plural = _('Страницы')
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('core:page_detail', kwargs={'slug': self.slug})
