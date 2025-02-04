#!/usr/bin/env bash
#
#  Copyright 2023 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#
echo "Starting App"
# set OPTUNAHUB_CACHE_HOME to ./.cache
export OPTUNAHUB_CACHE_HOME=./.cache

streamlit run streamlit_app_dr.py --server.port 8080 --browser.gatherUsageStats False
