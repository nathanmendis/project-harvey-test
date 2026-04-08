from django import forms
from core.models.invite import Invite
from core.models.recruitment import Candidate, JobRole, Interview

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['candidate', 'interviewer', 'date_time', 'interview_type', 'location', 'status', 'description']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
            'interviewer': forms.Select(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
            'date_time': forms.DateTimeInput(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'type': 'text'}),
            'interview_type': forms.Select(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
            'location': forms.TextInput(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'Zoom Link or Office Location'}),
            'status': forms.Select(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-6 py-4.5 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'rows': 4, 'placeholder': 'Special instructions or notes...'}),
        }

class InviteForm(forms.ModelForm):
    class Meta:
        model = Invite
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
            'role': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
        }

class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['name', 'email', 'phone', 'resume_file', 'source', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': 'candidate@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': '+1 (555) 123-4567'}),
            'resume_file': forms.FileInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
            'source': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': 'LinkedIn, Referral, etc.'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all'}),
        }

class JobForm(forms.ModelForm):
    class Meta:
        model = JobRole
        fields = ['title', 'description', 'requirements', 'department']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': 'e.g., Senior Software Engineer'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'rows': 4, 'placeholder': 'Job description...'}),
            'requirements': forms.Textarea(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'rows': 4, 'placeholder': 'Required skills and qualifications...'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg shadow-sm placeholder-gray-500 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all', 'placeholder': 'e.g., Engineering, Marketing'}),
        }