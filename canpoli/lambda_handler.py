"""AWS Lambda handler using Mangum ASGI adapter."""

from mangum import Mangum

from canpoli.main import app

# Mangum adapter for AWS Lambda
# lifespan="off" because Lambda doesn't support ASGI lifespan events
handler = Mangum(app, lifespan="off")
