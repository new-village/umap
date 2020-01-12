from flask import Flask, render_template, request
from flask.json import jsonify
from flask_restful import Resource, Api
from flask_pymongo import PyMongo
from datetime import datetime, timedelta
from bson import json_util
from controller import race


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/umap"
mongo = PyMongo(app)
api = Api(app)


@app.route('/')
def index():
    return render_template('index.html')


class Races(Resource):
    def get(self):
        record = [rec for rec in mongo.db.races.find()]
        return jsonify(record)

    def post(self):
        # Set Collected Date Parameter
        if request.form.get("YYYYMM") is not None:
            now = datetime.strptime(request.form["YYYYMM"], "%Y%m")
        else:
            now = datetime.now() + timedelta(weeks=1)

        # Collect Race Data
        msg = race.bulk_collect(now.strftime('%Y'), now.strftime('%m'))
        return msg


class Race(Resource):
    def get(self, race_id):
        record = mongo.db.races.find_one({"_id": race_id})
        return jsonify(record)

    def post(self, race_id):
        # Collect Race Data
        msg = race.collect(race_id)
        return msg


api.add_resource(Races, '/races')
api.add_resource(Race, '/races/<string:race_id>')


if __name__ == '__main__':
    app.run(host="0.0.0.0")
