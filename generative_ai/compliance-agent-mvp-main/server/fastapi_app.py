import os
import importlib
import pkgutil
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

# Important to host the app as a DataRobot custom app
# Generally script_name will be something like https://app.datarobot.com/custom_applications/{appId}
script_name = os.environ.get("SCRIPT_NAME", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    
    # Startup: Load all controllers
    # Note: frontend_controller must be loaded last due to its catch-all route
    controllers_dir = Path(__file__).parent / "app" / "controllers"
    if controllers_dir.exists():
        # Import the controllers package
        import app.controllers as controllers
        
        # Collect all controller modules
        controller_modules = []
        frontend_controller_module = None
        
        # Iterate through all modules in the controllers package
        for importer, module_name, ispkg in pkgutil.iter_modules(controllers.__path__):
            if module_name.endswith("_controller"):
                # Import the controller module
                module = importlib.import_module(f"app.controllers.{module_name}")
                
                if hasattr(module, "router"):
                    # Separate frontend_controller to load it last
                    if module_name == "frontend_controller":
                        frontend_controller_module = (module_name, module)
                    else:
                        controller_modules.append((module_name, module))
        
        # Load API controllers first
        for module_name, module in controller_modules:
            app.include_router(module.router, prefix=script_name)
            print(f"Loaded controller: {module_name}")
        
        # Load frontend controller last (catch-all routes)
        if frontend_controller_module:
            module_name, module = frontend_controller_module
            app.include_router(module.router, prefix=script_name)
            print(f"Loaded controller: {module_name}")
    
    yield
    # Shutdown: cleanup if needed


# Initialize the FastAPI app with lifespan
app = FastAPI(debug=True, lifespan=lifespan)

# Allow all origins to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
