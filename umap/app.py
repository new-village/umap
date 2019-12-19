from flask import Flask, render_template
from flask_restful import Resource, Api
from datetime import datetime, timedelta
from controller import races

app = Flask(__name__)
api = Api(app)


@app.route('/')
def index():
    return render_template('index.html')


class Race(Resource):
    def get(self):
        return {'HelloWorld': 'GET'}

    def post(self):
        # Collect This Month Races
        now = datetime.now() + timedelta(weeks=1)
        msg = races.bulk_collect(now.strftime('%Y'), now.strftime('%m'))
        return {'POST': str(msg)}


api.add_resource(Race, '/races')

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
