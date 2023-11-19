from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class LogMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resourceId = db.Column(db.String(255))
    parentResourceId = db.Column(db.String(255))

class LogData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(50))
    message = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime)
    traceId = db.Column(db.String(255))
    spanId = db.Column(db.String(255))
    commit = db.Column(db.String(255))
    log_metadata_id = db.Column(db.Integer, db.ForeignKey('log_metadata.id'))
    log_metadata = db.relationship('LogMetadata', backref='logs')
