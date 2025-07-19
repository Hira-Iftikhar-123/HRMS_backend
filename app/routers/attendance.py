from fastapi import APIRouter

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"]
)

# Add attendance-related endpoints here 