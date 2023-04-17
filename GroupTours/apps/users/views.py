from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

User = get_user_model()

class UserListView(ListView):
    model = User
    template_name = 'user_list.html'

class UserDetailView(DetailView):
    model = User
    template_name = 'user_detail.html'

class UserCreateView(CreateView):
    model = User
    template_name = 'user_form.html'
    fields = ('email', 'first_name', 'last_name', 'password')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data.get('password'))
        user.save()
        return redirect('user_detail', pk=user.pk)

class UserUpdateView(UpdateView):
    model = User
    template_name = 'user_form.html'
    fields = ('email', 'first_name', 'last_name', 'password')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data.get('password'))
        user.save()
        return redirect('user_detail', pk=user.pk)

class UserDeleteView(DeleteView):
    model = User
    template_name = 'user_confirm_delete.html'
    success_url = '/'
