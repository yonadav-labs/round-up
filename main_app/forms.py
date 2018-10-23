from __future__ import unicode_literals
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import UsernameField
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field
from django.core.validators import RegexValidator
from . import models
from main_app.models import StoreCharityHistory, Charities


####################################
# Form Definition Starts
####################################

class ToCForm(forms.Form):
    user_consent = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        super(ToCForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        self.fields['user_consent'].required = True
        self.initial['user_consent'] = False
        self.fields['user_consent'].label = "I consent to the apps terms and conditions."
        self.fields['user_consent'].help_text = "Please review the terms and conditions prior to accepting the agreement."

        self.helper.layout = Layout(
            Div(
                Field('user_consent'),
                css_class="Polaris-FormLayout")
        )

    def clean_user_consent(self):
        form_data = self.cleaned_data['user_consent']

        if form_data != True:
            raise ValidationError('You must agree to the terms and conditions in order to proceed.')

        return form_data


class ProfileSetupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileSetupForm, self).__init__(*args, **kwargs)

        instance = getattr(self, 'instance', None)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        self.fields['marketing_first_name'].label = 'First Name'
        self.fields['marketing_first_name'].required = True
        self.fields['marketing_last_name'].label = 'Last Name'
        self.fields['marketing_last_name'].required = True
        self.fields['marketing_email'].label = 'Contact Email'
        self.fields['marketing_email'].required = True

        self.fields['accepts_marketing_emails'].required = False
        self.initial['accepts_marketing_emails'] = True
        self.fields['accepts_marketing_emails'].label = "I want to receive promotional emails and other awesome content."

        self.fields['accepts_status_emails'].required = False
        self.initial['accepts_status_emails'] = True
        self.fields['accepts_status_emails'].label = "I want to receive emails about DropShop product updates and statuses."

        self.helper.layout = Layout(
                    Div(
                        Div(
                            Div(
                                Div(
                                    Field('marketing_first_name'),
                                    Field('marketing_last_name'),
                                    css_class="Polaris-FormLayout__Items"),
                            css_class="", role="group"),
                        css_class="Polaris-FormLayout"),
                        Div(
                            Field('marketing_email', placeholder="Where can we reach you?"),
                            css_class="Polaris-FormLayout"),
                        css_class='Polaris-Card__Section')
        )

        if instance.setup_required:
            self.helper.layout.append(
                Div(
                    Div(
                        Field('accepts_marketing_emails'),
                        css_class="Polaris-FormLayout"),
                    css_class='Polaris-Card__Section'))

            self.helper.layout.append(
                Div(
                    Div(
                        Field('accepts_status_emails'),
                        css_class="Polaris-FormLayout"),
                    css_class='Polaris-Card__Section'))

    class Meta:
        model = models.UserProfile
        exclude = ['user','display_timezone','iana_timezone','latest_product_sync_time', 'setup_required']


class CharityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CharityForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        self.helper.layout = Layout(
            Div(
                Div(Field('selected_charity'), css_class='col-xs-12'),
                css_class="row")
        )

    class Meta:
        model = StoreCharityHistory
        exclude = ['store']


class ContactForm(forms.Form):
    full_name = forms.CharField(required=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = forms.CharField(validators=[phone_regex], max_length=17) # validators should be a list
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        self.helper.layout = Layout(
            Div(
                Div(
                    Field('full_name'),
                    css_class="col-xs-12"),
                Div(
                    Field('phone_number'),
                    css_class="col-xs-12"),
                Div(
                    Field('message'),
                    css_class="col-xs-12"),
                css_class="row")
        )


class UninstallAppForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(UninstallAppForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'


class AdminAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = UsernameField(
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': ''}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
    )

    error_messages = {
        'invalid_login':
            "Please enter a correct %(username)s and password. Note that both "
            "fields may be case-sensitive."
        ,
        'inactive': "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super(AdminAuthenticationForm, self).__init__(*args, **kwargs)

        # Set the label for the "username" field.
        UserModel = get_user_model()
        self.username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': 'Username'},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.

        We have switched admin login to check if the user has a corresponding
        admin profile attached to their account.

        If the given user cannot log in, this method should raise a
        ``forms.ValidationError``.

        If the given user may log in, this method should return None.
        """
        try:
            if not user.adminprofile.is_admin:
                raise forms.ValidationError(
                    self.error_messages['not allowed'],
                    code='not-allowed',
                )
        except ObjectDoesNotExist:
            return None

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class StoreFilterFormHelper(FormHelper):
    form_method = 'GET'
    form_tag = False
    form_show_labels = False

    layout = Layout(
            Field('myshopify_domain', placeholder="Filter by store url...", css_class="pull-left"),
            Field('userprofile__name', placeholder="Filter by store name...", css_class="pull-left"),
    )


class CharityFilterFormHelper(FormHelper):
    form_method = 'GET'
    form_tag = False
    form_show_labels = False

    layout = Layout(
            Field('name', placeholder="Filter by charity name...", css_class="pull-left"),
            Field('website', placeholder="Filter by charity url...", css_class="pull-left"),
    )


class TransferFilterFormHelper(FormHelper):
    form_method = 'GET'
    form_tag = False
    form_show_labels = False

    layout = Layout(
            Field('customer__user__myshopify_domain', placeholder="Filter by store name...", css_class="pull-left"),
    )


class AdminCharityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AdminCharityForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Div(
                Div(Field('name', placeholder="Charity name..."), css_class='col-xs-12 col-md-6'),
                Div(Field('website', placeholder="Website URL of charity..."), css_class='col-xs-12 col-md-6'),
                Div(Field('charity_logo'), css_class='col-xs-12'),
                Div(Field('description', placeholder="Provide a description of this charity..."), css_class='col-xs-12'),
                css_class="row"
            )
        )

    class Meta:
        model = Charities
        fields = ['name', 'website', 'description', 'charity_logo']