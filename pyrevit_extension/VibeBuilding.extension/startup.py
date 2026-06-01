# -*- coding: utf-8 -*-
"""VibeBuilding startup script - initializes HTTP API routes for AI-driven BIM modeling.

This script runs when Revit starts with the VibeBuilding extension loaded.
It registers the API routes and activates the HTTP server.
"""

from pyrevit import routes
from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)

# Import and register API routes
try:
    import vb_api
    mlogger.info("VibeBuilding API routes registered")

    # Activate the routes server
    server = routes.activate_server()
    if server:
        mlogger.info("VibeBuilding HTTP server started on port {}".format(server.port))
    else:
        mlogger.warning("Failed to start VibeBuilding HTTP server")

except Exception as e:
    mlogger.error("Failed to initialize VibeBuilding: {}".format(str(e)))
