from django.views.generic import ListView, DetailView
from .models import Category


class CategoryListView(ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(is_active=True)


class CategoryDetailView(DetailView):
    model = Category
    template_name = "categories/category_detail.html"
    context_object_name = "category"

    def get_queryset(self):
        return Category.objects.filter(is_active=True)
