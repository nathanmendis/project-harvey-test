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
            'email': forms.EmailInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
            'role': forms.Select(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
        }

class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['name', 'email', 'phone', 'resume_file', 'source', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'candidate@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': '+1 (555) 123-4567'}),
            'resume_file': forms.FileInput(attrs={'class': 'block w-full text-xs text-slate-400 file:mr-6 file:py-3 file:px-8 file:rounded-xl file:border-0 file:text-[10px] file:font-black file:uppercase file:tracking-widest file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 file:cursor-pointer transition-all file:shadow-xl file:shadow-indigo-100'}),
            'source': forms.TextInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'LinkedIn, Referral, etc.'}),
            'status': forms.Select(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold'}),
        }

class JobForm(forms.ModelForm):
    class Meta:
        model = JobRole
        fields = ['title', 'description', 'requirements', 'department']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'e.g., Senior Software Engineer'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'rows': 4, 'placeholder': 'Job description...'}),
            'requirements': forms.Textarea(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'rows': 4, 'placeholder': 'Required skills and qualifications...'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-900 placeholder-slate-400 focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 focus:outline-none transition-all font-bold', 'placeholder': 'e.g., Engineering, Marketing'}),
        }