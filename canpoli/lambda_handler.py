"""AWS Lambda handler using Mangum ASGI adapter."""

from mangum import Mangum

from canpoli.app import create_app

# Mangum adapter for AWS Lambda
# lifespan="off" because Lambda doesn't support ASGI lifespan events
handler = Mangum(create_app(), lifespan="off")
