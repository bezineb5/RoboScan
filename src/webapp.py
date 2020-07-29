import logging
import pathlib
import sys
import threading
import queue
from typing import Any, Optional
from http import HTTPStatus

from flask import Flask
from flask_restx import Api, Resource, fields
from flask_socketio import SocketIO

from scanner import scanner, utils, archive, session
from scanner.hardware import camera

log = logging.getLogger(__name__)

SOCKET_IO_NAMESPACE = "/scanner_events"

thread = None
thread_lock = threading.Lock()
message_queue: queue.SimpleQueue = queue.SimpleQueue()

archive_storage = archive.Archive()
capture_camera: Optional[camera.Camera] = None
the_scanner: Optional[scanner.Scanner] = None

app = Flask(__name__)
socketio = SocketIO(app)

api = Api(app, version='1.0', title='PiScanner API',
          description='PiScanner API', doc="/doc/", base_url='/'
          )
ns = api.namespace('scanner', description='Scanner API')

file_details = api.model('File', {
    'name': fields.String(required=True, description='The file name')
})

file_operation_result = api.model('FileOperationResult', {
    'count': fields.Integer(required=True, description='The number of files modified'),
})

status_model = api.model('Status', {
    'success': fields.Boolean(description="True if the operation is succesful"),
})

session_id = api.model('Session', {
    'id': fields.Integer(required=True, description='Session ID'),
})

session_details = api.model('SessionDetails', {
    'id': fields.Integer(required=True, description='Session ID'),
    'is_scanning': fields.Boolean(required=True, description='True if a scan is on-going'),
})

skip_holes_model = api.model('SkipHoles', {
    'number_of_holes': fields.Integer(required=True, description='Number of holes to skip'),
})

error_model = api.model('Error', {
    'message': fields.String(required=True, description='Error message')
})


@ns.route('/archive/')
class ArchiveResource(Resource):
    '''Shows a list of all archived files, and lets you manage them'''
    # @ns.doc('list_archive')
    # @ns.marshal_list_with(file_details)
    # def get(self):
    #     '''List all files'''
    #     return DAO.todos

    @ns.doc('move_to_archive')
    @ns.marshal_with(file_operation_result, code=HTTPStatus.CREATED.value)
    def post(self):
        '''Move all photos to the archive'''
        count = archive_storage.move_to_archive()
        return {"count": count}, HTTPStatus.CREATED.value

    @ns.doc('delete_archive')
    @ns.marshal_with(file_operation_result, code=HTTPStatus.OK.value)
    def delete(self):
        '''Delete all photos from the archive'''
        count = archive_storage.delete_archive()
        return {"count": count}


@ns.route('/camera/reset/')
class CameraResetModel(Resource):
    @ns.doc('reset_camera')
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        '''
        Reset the connection to the camera
     
        :raises CameraException: In case of error when connecting to the camera
        '''
        capture_camera.connect()
        return {"success": True}


@ns.route('/session/')
class SessionListResource(Resource):
    @ns.doc('list_sessions')
    @ns.marshal_list_with(session_id, code=HTTPStatus.OK.value)
    def get(self):
        '''List all active sessions'''
        session_ids = session.list_session_ids()
        return [{"id": sid} for sid in session_ids ]

    @ns.doc('init_session')
    @ns.marshal_with(session_id, code=HTTPStatus.CREATED.value)
    def post(self):
        '''
        Starts a new scanning session
        
        :raises CameraException: In case of error when connecting to the camera
        '''
        log.info('init_session')

        the_session = session.get_or_new_session(
            capture_camera, the_scanner, {}, post_message)
        return {"id": the_session.id}, HTTPStatus.CREATED.value


@ns.route('/session/<int:session_id>/')
class SessionResource(Resource):
    @ns.doc('session_details')
    @ns.marshal_with(session_details, code=HTTPStatus.OK.value)
    def get(self, session_id: int):
        '''Get session details'''
        the_session = session.get_session(session_id)
        return {
            "id": the_session.id,
            "is_scanning": the_session.is_scanning,
        }

    @ns.doc('skip_holes')
    @ns.expect(skip_holes_model, validate=True)
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def put(self, session_id: int):
        '''Skip the given number of holes'''
        the_session = session.get_session(session_id)
        number_of_holes = api.payload['number_of_holes']
        the_session.skip_holes_async(number_of_holes)
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('start_scan')
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def post(self, session_id: int):
        '''Start scanning'''
        the_session = session.get_session(session_id)
        the_session.start_scan_async()
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('stop_session')
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def delete(self, session_id: int):
        '''Stop scanning and finishes the session'''
        the_session = session.get_session(session_id)
        the_session.stop()
        return {"success": True}


@api.errorhandler(camera.CameraException)
@api.marshal_with(error_model, code=500)
def handle_camera_exception(error):
    '''Camera error'''
    return {'message': error.message}, 500


# Static content / homepage
@app.route('/')
def homepage():
    return app.send_static_file('index.html')


# Websocket
@socketio.on('connect', namespace=SOCKET_IO_NAMESPACE)
def scanner_events_connect():
    log.info('Client connected')
    with thread_lock:
        global thread
        if thread is None:
            thread = socketio.start_background_task(message_broadcast)


@socketio.on('disconnect', namespace=SOCKET_IO_NAMESPACE)
def scanner_events_disconnect():
    log.info('Client disconnected')


@api.errorhandler
def default_error_handler(error):
    '''Default error handler'''
    log.error(error)
    return {'message': str(error)}, getattr(error, 'code', 500)


def message_broadcast():
    while True:
        subject, payload = message_queue.get()
        socketio.emit(subject, payload, namespace=SOCKET_IO_NAMESPACE)


def post_message(subject: str, payload: Any):
    if thread is not None:
        message_queue.put((subject, payload))


def main() -> None:
    args = utils.parse_arguments(is_webserver=True)
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)

    destination_path = pathlib.Path(args.destination)
    archive_storage.photos_path = destination_path
    archive_storage.archive_path = pathlib.Path(args.archive)

    global capture_camera
    capture_camera = utils.get_camera_type(args.dryrun)(destination_path)

    global the_scanner
    the_scanner = scanner.Scanner(
        args.led, args.backlight, args.pin1, args.pin2, args.pin3, args.pin4)

    # Start web server
    socketio.run(app, host='0.0.0.0', port=args.port, debug=args.verbose)


if __name__ == "__main__":
    main()
