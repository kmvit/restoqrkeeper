from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView
from .models import Page


class PageDetailView(DetailView):
    model = Page
    template_name = 'core/page_detail.html'
    context_object_name = 'page'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
        return queryset
