from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={
            'class': 'login-form',
            'placeholder': 'Digite o seu código de usuário',
        }),
        error_messages={
            'required': 'Por favor, insira seu e-mail.',
        }
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'login-form',
            'placeholder': 'Digite sua senha',
        }),
        error_messages={
            'required': 'Por favor, insira sua senha.',
        }
    )