from django import forms
from core.models.invite import Invite

class InviteForm(forms.ModelForm):
    class Meta:
        model = Invite
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
            'role': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
        }
