from flask import Flask, render_template
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)


@app.route('/')
def index():
    return render_template('index.html')


class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}


api.add_resource(HelloWorld, '/api/')

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
