from flask import Flask, request, jsonify, render_template
from flask_restful import Api, Resource, reqparse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from models import db, LogMetadata, LogData
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///logs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
api = Api(app)
es = Elasticsearch(['http://localhost:9200'])

with app.app_context():
    db.create_all()

class LogIngestor(Resource):
    def post(self):
        try:
            log_data = request.json
            log_data['@timestamp'] = datetime.utcnow()

            # Ingest into Elasticsearch
            es.index(index='logs', body=log_data)

            # Ingest into SQLite
            metadata = LogMetadata(resourceId=log_data.get('resourceId'), parentResourceId=log_data.get('metadata', {}).get('parentResourceId'))
            db.session.add(metadata)
            db.session.commit()

            log_entry = LogData(
                level=log_data.get('level'),
                message=log_data.get('message'),
                timestamp=log_data.get('@timestamp'),
                traceId=log_data.get('traceId'),
                spanId=log_data.get('spanId'),
                commit=log_data.get('commit'),
                metadata=metadata
            )
            db.session.add(log_entry)
            db.session.commit()

            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

api.add_resource(LogIngestor, '/ingest')

class LogQuery(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('q', type=str, help='Search query')
        parser.add_argument('level', type=str, help='Filter by level')
        parser.add_argument('message', type=str, help='Filter by message')
        parser.add_argument('resourceId', type=str, help='Filter by resourceId')
        parser.add_argument('timestamp', type=str, help='Filter by timestamp')
        parser.add_argument('traceId', type=str, help='Filter by traceId')
        parser.add_argument('spanId', type=str, help='Filter by spanId')
        parser.add_argument('commit', type=str, help='Filter by commit')
        parser.add_argument('parentResourceId', type=str, help='Filter by metadata.parentResourceId')
        parser.add_argument('start_date', type=str, help='Search logs after this date (format: YYYY-MM-DDTHH:MM:SSZ)')
        parser.add_argument('end_date', type=str, help='Search logs before this date (format: YYYY-MM-DDTHH:MM:SSZ)')

        args = parser.parse_args()
        query = args.get('q', '')
        filters = {k: v for k, v in args.items() if v is not None and k not in ['q', 'start_date', 'end_date']}

        try:
            s = Search(using=es, index='logs').query("match", _all=query)
            for key, value in filters.items():
                s = s.filter('term', **{key: value})

            if args['start_date'] and args['end_date']:
                s = s.filter('range', **{'@timestamp': {'gte': args['start_date'], 'lte': args['end_date']}})

            result = s.execute()
            hits = [hit['_source'] for hit in result.hits]
            return jsonify({"status": "success", "data": hits}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

api.add_resource(LogQuery, '/query')

# New route for the web UI
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=3000)
