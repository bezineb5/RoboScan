import logging
import pathlib
import sys
import threading
import queue
from typing import Any, Callable
from http import HTTPStatus

from flask import Flask
from flask_restx import Api, Resource, fields
from flask_socketio import SocketIO

from scanner import scanner, utils, archive, session
from scanner import exif_tagger
from scanner import frame_counter
from scanner.exif import develop_process, film_type, films
from scanner.hardware import camera
from scanner.metadata import MetaData
from scanner.session import SessionSettings

log = logging.getLogger(__name__)

SOCKET_IO_NAMESPACE = "/scanner_events"
METADATA_PREFIX = "metadata_"

thread = None
thread_lock = threading.Lock()
message_queue: queue.SimpleQueue = queue.SimpleQueue()

archive_storage = archive.Archive()
capture_camera: camera.Camera
the_scanner: scanner.Scanner
exif_tag_func: Callable[[pathlib.Path, MetaData,
                         Callable[[pathlib.Path], None]], None]

# Web server
app = Flask(__name__)
socketio = SocketIO(app)

# REST API
api = Api(app, version='1.0', title='RoboScan API',
          description='RoboScan API', doc="/doc/", base_url='/'
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

film_type_model = api.model('FilmType', {
    'type': fields.String(required=True, description='Film type, as supported by AnalogExif: http://analogexif.sourceforge.net/help/analogexif-xmp.php')
})

frame_count_model = api.model('FrameCount', {
    'frame': fields.String(required=True, description='Frame count, as read on the film'),
})

develop_process_model = api.model('DevelopProcess', {
    'process': fields.String(required=True, description='Film development process name'),
})

film_model = api.model('Film', {
    'make': fields.String(required=True, description='Film brand name'),
    'name': fields.String(required=True, description='Film name (without the brand)'),
})

# Parsers
new_session_parser = api.parser()
new_session_parser.add_argument(
    'initial_frame', type=str, location='json', help='Frame name of the first photo')
new_session_parser.add_argument('max_number_of_files', type=int, default=1,
                                location='json', help='Maximum number of files to download per photo')
new_session_parser.add_argument('delete_photo_after_download', type=bool, default=False,
                                location='json', help='Should photos be deleted from the camera after download?')

new_session_parser.add_argument('metadata_lens_serial_number',
                                type=str, location='json', help='Metadata: lens serial number')
new_session_parser.add_argument(
    'metadata_roll_id', type=str, location='json', help='Metadata: roll identifier')
new_session_parser.add_argument(
    'metadata_film_maker', type=str, location='json', help='Metadata: film maker')
new_session_parser.add_argument(
    'metadata_film', type=str, location='json', help='Metadata: film (including the manufacturer)')
new_session_parser.add_argument(
    'metadata_film_alias', type=str, location='json', help='Metadata: film alias')
new_session_parser.add_argument(
    'metadata_film_grain', type=int, location='json', help='Metadata: film RMS value')
new_session_parser.add_argument(
    'metadata_film_type', type=str, location='json', help='Metadata: film type')
new_session_parser.add_argument(
    'metadata_developer', type=str, location='json', help='Metadata: developer used')
new_session_parser.add_argument(
    'metadata_develop_process', type=str, location='json', help='Metadata: development process')
new_session_parser.add_argument('metadata_developer_maker', type=str,
                                location='json', help='Metadata: developer manufacturer')
new_session_parser.add_argument('metadata_developer_dilution',
                                type=str, location='json', help='Metadata: developer dilution')
new_session_parser.add_argument(
    'metadata_develop_time', type=str, location='json', help='Metadata: development time')
new_session_parser.add_argument(
    'metadata_lab', type=str, location='json', help='Metadata: processing lab')
new_session_parser.add_argument(
    'metadata_lab_address', type=str, location='json', help='Metadata: processing lab address')
new_session_parser.add_argument(
    'metadata_filter', type=str, location='json', help='Metadata: filter name')


@ns.route('/archive/')
class ArchiveResource(Resource):
    """Shows a list of all archived files, and lets you manage them"""
    # @ns.doc('list_archive')
    # @ns.marshal_list_with(file_details)
    # def get(self):
    #     """List all files"""
    #     return DAO.todos

    @ns.doc('move_to_archive')
    @ns.marshal_with(file_operation_result, code=HTTPStatus.CREATED.value)
    def post(self):
        """Move all photos to the archive"""
        count = archive_storage.move_to_archive()
        return {"count": count}, HTTPStatus.CREATED.value

    @ns.doc('delete_archive')
    @ns.marshal_with(file_operation_result, code=HTTPStatus.OK.value)
    def delete(self):
        """Delete all photos from the archive"""
        count = archive_storage.delete_archive()
        return {"count": count}


@ns.route('/camera/reset/')
class CameraResetModel(Resource):
    @ns.doc('reset_camera')
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Reset the connection to the camera

        :raises CameraException: In case of error when connecting to the camera
        """
        capture_camera.connect()
        return {"success": True}


@ns.route('/session/')
class SessionListResource(Resource):
    @ns.doc('list_sessions')
    @ns.marshal_list_with(session_id, code=HTTPStatus.OK.value)
    def get(self):
        """List all active sessions"""
        session_ids = session.list_session_ids()
        return [{"id": sid} for sid in session_ids]

    @ns.doc('init_session')
    @ns.expect(new_session_parser)
    @ns.marshal_with(session_id, code=HTTPStatus.CREATED.value)
    def post(self):
        """
        Starts a new scanning session

        :raises camera.CameraException: In case of error when connecting to the camera
        """
        log.info('init_session')

        args = new_session_parser.parse_args()
        log.info("args: %s", args)
        initial_frame = frame_counter.from_string(args.get('initial_frame'))
        metadata = {k[len(METADATA_PREFIX):]: v for k,
                    v in args.items() if k.startswith(METADATA_PREFIX)}
        log.info("Found metadata: %s", metadata)

        settings = SessionSettings(
            destination_storage=archive_storage.photos_path,
            initial_frame=initial_frame,
            max_number_of_files=args.get('max_number_of_files', 1),
            delete_photo_after_download=args.get(
                'delete_photo_after_download', False),
            metadata=MetaData(exposure_number=None, **metadata)
        )

        new_session_parser.add_argument(
            'initial_frame', type=str, help='Frame name of the first photo')
        new_session_parser.add_argument(
            'max_number_of_files', type=int, help='Maximum number of files to download per photo')

        new_session_parser.add_argument(
            'metadata_lens_serial_number', type=str, help='Metadata: lens serial number')

        the_session = session.get_or_new_session(
            capture_camera, the_scanner, settings, post_message, exif_tag_func)
        return {"id": the_session.id}, HTTPStatus.CREATED.value


@ns.route('/session/<int:session_id>/')
class SessionResource(Resource):
    @ns.doc('session_details')
    @ns.marshal_with(session_details, code=HTTPStatus.OK.value)
    def get(self, session_id: int):
        """Get session details"""
        the_session = session.get_session(session_id)
        return {
            "id": the_session.id,
            "is_scanning": the_session.is_scanning,
        }

    @ns.doc('skip_holes')
    @ns.expect(skip_holes_model, validate=True)
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def put(self, session_id: int):
        """Skip the given number of holes"""
        the_session = session.get_session(session_id)
        number_of_holes = api.payload['number_of_holes']
        the_session.skip_holes_async(number_of_holes)
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('start_scan')
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def post(self, session_id: int):
        """Start scanning"""
        the_session = session.get_session(session_id)
        the_session.start_scan_async()
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('stop_session')
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def delete(self, session_id: int):
        """Stop scanning and finishes the session"""
        the_session = session.get_session(session_id)
        the_session.stop()
        return {"success": True}


@ns.errorhandler(camera.CameraException)
@ns.marshal_with(error_model, code=500)
def handle_camera_exception(error):
    """
    Camera error
    """
    log.error("Error with the camera", error)
    return {'message': error.message}, 500


# Reference data
@ns.route('/reference/film_type/')
class FilmTypeListResource(Resource):
    @ns.doc('list_film_type')
    @ns.marshal_list_with(film_type_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List all film types
        """
        return [{'type': t} for t in film_type.get_film_types()]


@ns.route('/reference/frame_count/')
class FrameCountListResource(Resource):
    @ns.doc('list_frame_count')
    @ns.marshal_list_with(frame_count_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List frame counts
        """
        return [{'frame': f} for f in frame_counter.list_typical_frames()]


@ns.route('/reference/develop_process/')
class DevelopProcessListResource(Resource):
    @ns.doc('list_develop_process')
    @ns.marshal_list_with(develop_process_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List development processes
        """
        return [{'process': p} for p in develop_process.get_develop_processes()]


@ns.route('/reference/film/')
class FilmListResource(Resource):
    @ns.doc('list_film')
    @ns.marshal_list_with(film_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List films
        """
        return [{'make': m, 'name': n} for m, n in films.get_all_films()]


# Static content / homepage
@app.route('/')
def homepage():
    return app.send_static_file('index.html')


# Healthcheck
@app.route('/ping')
def healthcheck():
    return {'success': True}


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


@ns.errorhandler(Exception)
def default_error_handler(error):
    """Default error handler"""
    log.error(error)
    return {'message': str(error)}, getattr(error, 'code', 500)


def message_broadcast():
    while True:
        subject, payload = message_queue.get()
        socketio.emit(subject, payload, namespace=SOCKET_IO_NAMESPACE)


def post_message(subject: str, payload: Any):
    if thread is not None:
        message_queue.put((subject, payload))


def _ensure_path(pth: str) -> pathlib.Path:
    the_path = pathlib.Path(pth)
    the_path.mkdir(parents=True, exist_ok=True)
    return the_path


def main() -> None:
    args = utils.parse_arguments(is_webserver=True)

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)

    # Storage
    archive_storage.photos_path = _ensure_path(args.destination)
    archive_storage.archive_path = _ensure_path(args.archive)
    temporary_path = _ensure_path(args.temp)

    global capture_camera
    capture_camera = utils.get_camera_type(args.dryrun)(temporary_path)

    global the_scanner
    the_scanner = scanner.Scanner(
        args.led, args.infrared, args.backlight, args.pin1, args.pin2, args.pin3, args.pin4)

    global exif_tag_func
    exif_tag_func = exif_tagger.async_tagger()

    # See: https://github.com/noirbizarre/flask-restplus/issues/693
    if args.verbose:
        app.config["PROPAGATE_EXCEPTIONS"] = False

    # Start web server
    socketio.run(app, host='0.0.0.0', port=args.port, debug=args.verbose)


if __name__ == "__main__":
    main()
