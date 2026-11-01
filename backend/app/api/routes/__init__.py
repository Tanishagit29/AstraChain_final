from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.forecast import router as forecast_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.suppliers import router as suppliers_router
from app.api.routes.routes import router as routes_router
from app.api.routes.wastage import router as wastage_router
from app.api.routes.ai import router as ai_router
from app.api.routes.automation import router as automation_router
from app.api.routes.reports import router as reports_router
from app.api.routes.data_collection import router as data_collection_router
from app.api.routes.multi_agent import router as multi_agent_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.rio_mart import router as rio_mart_router
from app.api.routes.notifications import router as notifications_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(forecast_router)
api_router.include_router(inventory_router)
api_router.include_router(suppliers_router)
api_router.include_router(routes_router)
api_router.include_router(wastage_router)
api_router.include_router(ai_router)
api_router.include_router(automation_router)
api_router.include_router(reports_router)
api_router.include_router(data_collection_router)
api_router.include_router(multi_agent_router)
api_router.include_router(pipeline_router)
api_router.include_router(rio_mart_router)
api_router.include_router(notifications_router)
