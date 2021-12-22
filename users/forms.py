from django import forms


class SignupBusiness(forms.Form):
    company_name = forms.CharField(label='Company Name', max_length=100)
    first_name = forms.CharField(label='First Name', max_length=100)
    last_name = forms.CharField(label='Last Name', max_length=100)
    email = forms.EmailField(label='Email', max_length=250)
    username = forms.CharField(label='Username', max_length=32)

