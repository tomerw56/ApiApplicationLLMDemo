# app.py
from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime

app = FastAPI(title="LLM-demo API (mock project service)")

# -----------------------------
# Pydantic models (schemas)
# -----------------------------
class GetSessionIn(BaseModel):
    project_name: str = Field(..., min_length=1)


class StructureField(BaseModel):
    name: str
    type: str  # free-form type string (e.g. "string", "int", "embedding", "object", ...)
    required: Optional[bool] = False
    meta: Optional[Dict[str, Any]] = None


class ProjectStructure(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    fields: List[StructureField] = Field(..., min_items=0)

    @model_validator(mode="after")
    def check_unique_field_names(self):
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("fields must have unique names")
        return self


class SetStructureIn(BaseModel):
    session_key: str
    structure: ProjectStructure



class ProjectMessage(BaseModel):
    name: str = Field(..., min_length=1)
    created_at: datetime | None = None
    payload: list[Any]

    @model_validator(mode="before")
    def ensure_timestamp(cls, values):
        if "created_at" not in values or values.get("created_at") is None:
            values["created_at"] = datetime.utcnow()
        return values


class SetMessageIn(BaseModel):
    session_key: str
    message: ProjectMessage


# -----------------------------
# In-memory storage
# -----------------------------
# sessions: session_key -> project_name
SESSIONS: Dict[str, str] = {}

# projects: project_name -> {"structures": {name: ProjectStructure}, "messages": {name: ProjectMessage}}
PROJECTS: Dict[str, Dict[str, Dict[str, Any]]] = {}


# -----------------------------
# Helper utilities
# -----------------------------
def get_project_by_session(session_key: str) -> str:
    project = SESSIONS.get(session_key)
    if project is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session_key")
    return project


def ensure_project_exists(project_name: str):
    if project_name not in PROJECTS:
        PROJECTS[project_name] = {"structures": {}, "messages": {}}


# Very small validation: ensure message content keys correspond to declared structure fields (if a structure used)
# We'll allow messages that don't match any structure, but when a message refers to structure_name in payload we'll validate.
def validate_message_against_structures(project_name: str, message: ProjectMessage):
    # Optional: if message.payload contains a special key "__structure__" that names a structure, validate:
    payload = message.payload
    for item in payload:
        struct_name = item.get("structure_name")
        if struct_name:
            structs = PROJECTS[project_name]["structures"]
            if struct_name not in structs:
                raise HTTPException(status_code=422, detail=f"Referenced structure '{struct_name}' not found in project")

# -----------------------------
# Endpoints
# -----------------------------
@app.post("/get_session")
def get_session(body: GetSessionIn):
    """
    Create a session for a project_name and return a session_key.
    If project does not exist yet, it is created (empty).
    """
    project_name = body.project_name
    session_key = str(uuid4())
    SESSIONS[session_key] = project_name
    ensure_project_exists(project_name)
    return {"session_key": session_key, "project_name": project_name}


@app.get("/get_schema")
def get_schema():
    return {
        "set_structure": {
            "session_key": "string",
            "structure": {
                "name": "string",
                "fields": [
                    {"name": "string", "type": "string", "required": "bool"}
                ]
            }
        },
        "set_message": {
            "session_key": "string",
            "message": {
                "name": "string",
                "payload": [
                    {
                        "structure_name": "string",
                        "type": "string",
                        "values": [{"field": "value"}]
                     }
                ]


            }
        },
        "get_project_data": {
            "session_key": "string"
        }
    }


@app.post("/set_structure")
def set_structure(body: SetStructureIn):
    """
    Add or replace a ProjectStructure for the project bound to session_key.
    If a structure with the same name exists, it will be replaced.
    """
    session_key = body.session_key
    try:
        project_name = get_project_by_session(session_key)
    except HTTPException:
        raise

    structure = body.structure
    # Pydantic validation already applied when parsing SetStructureIn

    ensure_project_exists(project_name)
    PROJECTS[project_name]["structures"][structure.name] = structure
    return {"status": "ok", "project": project_name, "structure_added_or_replaced": structure.name}


@app.post("/set_message")
def set_message(body: SetMessageIn):
    """
    Add or replace a message for the project bound to session_key.
    If a message with the same name exists, it will be replaced.
    Basic validation against referenced structure (if present in payload).
    """
    print("got_set_message")
    session_key = body.session_key
    try:
        project_name = get_project_by_session(session_key)
    except HTTPException:
        raise

    message = body.message
    ensure_project_exists(project_name)
    print("project_exsists")

    # run lightweight validation logic:
    validate_message_against_structures(project_name, message)

    PROJECTS[project_name]["messages"][message.name] = message
    return {"status": "ok", "project": project_name, "message_added_or_replaced": message.name}


@app.get("/get_project_data")
def get_project_data(session_key: str = Query(..., min_length=1)):
    """
    Return all structures and messages for the project that corresponds to session_key.
    """
    try:
        project_name = get_project_by_session(session_key)
    except HTTPException:
        raise

    ensure_project_exists(project_name)
    structs = PROJECTS[project_name]["structures"]
    msgs = PROJECTS[project_name]["messages"]

    # convert models to dicts for JSON serialization
    def model_to_dict(m):
        if isinstance(m, ProjectStructure):
            return m.dict()
        if isinstance(m, ProjectMessage):
            return {
                "name": m.name,
                "created_at": m.created_at.isoformat(),
                "payload": m.payload
            }
        return m

    return {
        "project_name": project_name,
        "structures": {name: model_to_dict(s) for name, s in structs.items()},
        "messages": {name: model_to_dict(m) for name, m in msgs.items()},
    }


# -----------------------------
# Health and debug endpoints
# -----------------------------
@app.get("/_health")
def health():
    return {"status": "ok", "projects_count": len(PROJECTS), "sessions_count": len(SESSIONS)}
