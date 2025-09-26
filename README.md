# General
A project to demo API tool with ollama

# Prerquisits
- admin rights

# How to use ollama?
- install locall ollama, windows 
- ollama is on http://localhost:11434
- verifay activation with ```ollama --version``` and ```ollama run llama3``` with powershell

# app.py
We will setup an application to mock client server interaction
it i lanched via ```uvicorn```  use ```app:app --reload --port 8000```
the activation is best ```PS D:\RidaDemo\src> ..\.venv\Scripts\uvicorn.exe app:app --reload --port 8000``` 
you need to install ```pip install fastapi uvicorn[standard] pydantic```

swagger docs are on ```http://127.0.0.1:8000/docs```
