from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/reviews")
async def get_reviews(request: Request):
    store = request.app.state.store
    return JSONResponse(store.get_all())


@router.get("/reviews/{review_id}")
async def get_review(review_id: str, request: Request):
    store = request.app.state.store
    review = store.get(review_id)
    if not review:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(review)


@router.get("/stats")
async def get_stats(request: Request):
    store = request.app.state.store
    return JSONResponse(store.get_stats())
