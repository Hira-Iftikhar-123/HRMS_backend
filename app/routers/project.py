from fastapi import APIRouter

router = APIRouter(
    prefix="/projects",
    tags=["projects"]
)

# Add project-related endpoints here 