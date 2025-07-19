from fastapi import APIRouter

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

# Add task-related endpoints here 