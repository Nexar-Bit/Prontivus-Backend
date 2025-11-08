"""
Application monitoring and error tracking with Sentry
"""
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration


def init_sentry():
    """
    Initialize Sentry for error tracking and performance monitoring
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    sentry_environment = os.getenv("SENTRY_ENVIRONMENT", "development")
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=sentry_environment,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                AsyncioIntegration(),
            ],
            # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
            traces_sample_rate=1.0 if sentry_environment == "development" else 0.1,
            # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions
            profiles_sample_rate=1.0 if sentry_environment == "development" else 0.1,
            # Enable release tracking
            release=os.getenv("APP_VERSION", "1.0.0"),
        )
        return True
    return False

