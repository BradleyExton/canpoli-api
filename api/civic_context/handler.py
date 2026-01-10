from mangum import Mangum

from api.civic_context.main import app

handler = Mangum(app, lifespan="off")
