Here are the setup instructions in a clear README.md format.

Project Harvey: AI-Powered HR Chatbot
🚀 Getting Started: Project Setup
Follow these commands in your terminal to set up the project on your local machine.

Step 1: Clone the Repository
Clone the project from GitHub and move into the project directory.

Bash

git clone https://github.com/nathanmendis/project-harvey.git
cd project-harvey
Step 2: Install Dependencies
Poetry will install all project dependencies from the pyproject.toml file into an isolated virtual environment.

Bash

poetry install
Step 3: Download the Local LLM Model
The project uses a local LLM for inference. You need to manually download the model file.

Create a directory for the model:

Bash

mkdir llm_models
Download the mistral-7b-instruct-v0.1.Q4_0.gguf file from the official GPT4All website.

Place the downloaded .gguf file inside the llm_models directory.

Step 4: Configure the Database
Run the migrate command to create the necessary database tables.

Bash

poetry run python manage.py migrate
Step 5: Create a Superuser
Create an admin account to access the Django admin panel.

Bash

poetry run python manage.py createsuperuser
Step 6: Run the Server
Start the development server and the Tailwind CSS watcher simultaneously with a single command.

Bash

poetry run python manage.py tailwind runserver
Your application will now be running and accessible at http://127.0.0.1:8000.
