from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

@csrf_exempt
@require_POST
@login_required
def upload_resume(request):
    """Handle resume file upload."""
    if 'resume' not in request.FILES:
        return JsonResponse({"error": "No file provided"}, status=400)
    
    file = request.FILES['resume']
    fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'resumes'))
    filename = fs.save(file.name, file)
    file_path = fs.path(filename)
    
    return JsonResponse({"file_path": file_path, "filename": filename})
