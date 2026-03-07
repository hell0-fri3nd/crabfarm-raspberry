
from flask import ( Flask )
from flask_cors import CORS
from routers import camera

app = Flask(__name__)
CORS(app,
    supports_credentials=True,
    origins=[
        "http://localhost:7987",
        "http://192.168.100.11:7987",
        "http://192.168.100.11:4572/",
        "http://0.0.0.0:4572/"
    ]
)


app.register_blueprint(camera)

if __name__ == '__main__':
    
    app.run(
        host='0.0.0.0',        
        debug=True,
        threaded=True,
        port=4573)