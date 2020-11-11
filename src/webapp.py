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

from scanner import scanner_device, utils, archive, session
from scanner import exif_tagger
from scanner import frame_counter
from scanner import detector_scanner
from scanner import settings
from scanner.exif import develop_process, film_type, films
from scanner.hardware import camera
from scanner.metadata import MetaData
from scanner.session import Session, SessionSettings, SessionDoesNotExist

log = logging.getLogger(__name__)

SOCKET_IO_NAMESPACE = "/scanner_events"
METADATA_PREFIX = "metadata_"

thread = None
thread_lock = threading.Lock()
message_queue: queue.SimpleQueue = queue.SimpleQueue()

archive_storage = archive.Archive()
capture_camera: camera.Camera
the_scanner: scanner_device.Scanner
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
    'feature_skip_hole': fields.Boolean(required=True, description='True if the scanner supports skipping holes'),
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

camera_setting_model = api.model('CameraSetting', {
    'value': fields.String(required=True, description='Camera setting value'),
    'active': fields.Boolean(required=False, description='True if it is the currently active setting'),
    'last_used': fields.Boolean(required=False, description='True if it is the setting used last time'),
})

session_settings_model = api.model('SessionSettings', {
    'initial_frame': fields.String(required=False, description='Frame name of the first photo'),
    'max_number_of_files': fields.Integer(required=False, description='Maximum number of files to download per photo'),
    'delete_photo_after_download': fields.Boolean(required=False, description='Should photos be deleted from the camera after download'),
    'metadata_lens_serial_number': fields.String(required=False, description='Metadata: lens serial number'),
    'metadata_roll_id': fields.String(required=False, description='Metadata: roll identifier'),
    'metadata_film_maker': fields.String(required=False, description='Metadata: film maker'),
    'metadata_film': fields.String(required=False, description='Metadata: film (including the manufacturer)'),
    'metadata_film_alias': fields.String(required=False, description='Metadata: film alias'),
    'metadata_film_grain': fields.Integer(required=False, description='Metadata: film RMS value'),
    'metadata_film_type': fields.String(required=False, description='Metadata: film type'),
    'metadata_developer': fields.String(required=False, description='Metadata: developer used'),
    'metadata_develop_process': fields.String(required=False, description='Metadata: development process'),
    'metadata_developer_maker': fields.String(required=False, description='Metadata: developer manufacturer'),
    'metadata_developer_dilution': fields.String(required=False, description='Metadata: developer dilution'),
    'metadata_develop_time': fields.String(required=False, description='Metadata: development time'),
    'metadata_lab': fields.String(required=False, description='Metadata: processing lab'),
    'metadata_lab_address': fields.String(required=False, description='Metadata: processing lab address'),
    'metadata_filter': fields.String(required=False, description='Metadata: filter name'),
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

camera_setting_parser = api.parser()
camera_setting_parser.add_argument(
    'value', type=str, location='json', help='Value of the camera setting to set')


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
class CameraResetResource(Resource):
    @ns.doc('reset_camera')
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Reset the connection to the camera

        :raises camera.CameraException: In case of error when connecting to the camera
        """
        capture_camera.connect()
        return {"success": True}


@ns.route('/camera/iso/')
class CameraIsoResource(Resource):
    @ns.doc('list_iso')
    @ns.marshal_list_with(camera_setting_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List of accepted values for the ISO camera setting
        """
        current_iso = capture_camera.iso
        last_used_iso = settings.get_settings().last_camera_settings.iso
        return [
            {
                'value': v,
                'active': v == current_iso,
                'last_used': v == last_used_iso,
            } for v in capture_camera.accepted_iso]

    @ns.doc('set_iso')
    @ns.expect(camera_setting_parser)
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Set the ISO of the camera

        :raises camera.CameraException: In case of error when connecting to the camera
        """

        # Parse webservice arguments
        args = camera_setting_parser.parse_args(strict=True)
        new_value = args.get('value')
        capture_camera.iso = new_value
        with settings.SettingsSaver() as s:
            s.last_camera_settings.iso = new_value
        return {"success": True}


@ns.route('/camera/shutter_speed/')
class CameraShutterSpeedResource(Resource):
    @ns.doc('list_shutter_speed')
    @ns.marshal_list_with(camera_setting_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List of accepted values for the shutter speed camera setting
        """
        current_shutter_speed = capture_camera.shutter_speed
        last_used_shutter_speed = settings.get_settings().last_camera_settings.shutter_speed
        return [
            {
                'value': v,
                'active': v == current_shutter_speed,
                'last_used': v == last_used_shutter_speed,
            } for v in capture_camera.accepted_shutter_speed]

    @ns.doc('set_shutter_speed')
    @ns.expect(camera_setting_parser)
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Set the shutter speed of the camera

        :raises camera.CameraException: In case of error when connecting to the camera
        """

        # Parse webservice arguments
        args = camera_setting_parser.parse_args(strict=True)
        new_value = args.get('value')
        capture_camera.shutter_speed = new_value
        with settings.SettingsSaver() as s:
            s.last_camera_settings.shutter_speed = new_value
        return {"success": True}


@ns.route('/camera/aperture/')
class CameraApertureResource(Resource):
    @ns.doc('list_aperture')
    @ns.marshal_list_with(camera_setting_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List of accepted values for the aperture camera setting
        """
        current_aperture = capture_camera.aperture
        last_used_aperture = settings.get_settings().last_camera_settings.aperture
        return [
            {
                'value': v,
                'active': v == current_aperture,
                'last_used': v == last_used_aperture,
            } for v in capture_camera.accepted_aperture]

    @ns.doc('set_aperture')
    @ns.expect(camera_setting_parser)
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Set the aperture of the camera

        :raises camera.CameraException: In case of error when connecting to the camera
        """

        # Parse webservice arguments
        args = camera_setting_parser.parse_args(strict=True)
        new_value = args.get('value')
        capture_camera.aperture = new_value
        with settings.SettingsSaver() as s:
            s.last_camera_settings.aperture = new_value
        return {"success": True}


@ns.route('/camera/exposure_compensation/')
class CameraExposureCompensationResource(Resource):
    @ns.doc('list_exposure_compensation')
    @ns.marshal_list_with(camera_setting_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List of accepted values for the exposure compensation camera setting
        """
        current_exposure_compensation = capture_camera.exposure_compensation
        last_used_exposure_compensation = settings.get_settings(
        ).last_camera_settings.exposure_compensation
        return [
            {
                'value': v,
                'active': v == current_exposure_compensation,
                'last_used': v == last_used_exposure_compensation,
            } for v in capture_camera.accepted_exposure_compensation]

    @ns.doc('set_exposure_compensation')
    @ns.expect(camera_setting_parser)
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def post(self):
        """
        Set the exposure_compensation of the camera

        :raises camera.CameraException: In case of error when connecting to the camera
        """

        # Parse webservice arguments
        args = camera_setting_parser.parse_args(strict=True)
        new_value = args.get('value')
        capture_camera.exposure_compensation = new_value
        with settings.SettingsSaver() as s:
            s.last_camera_settings.exposure_compensation = new_value
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
    @ns.response(500, 'Camera error', error_model)
    @ns.marshal_with(session_details, code=HTTPStatus.CREATED.value)
    def post(self):
        """
        Starts a new scanning session

        :raises camera.CameraException: In case of error when connecting to the camera
        """
        log.info('init_session')

        # Parse webservice arguments
        args = new_session_parser.parse_args(strict=True)

        initial_frame = frame_counter.from_string(args.get('initial_frame'))
        metadata = {k[len(METADATA_PREFIX):]: v for k,
                    v in args.items() if k.startswith(METADATA_PREFIX)}
        log.info("Found metadata: %s", metadata)

        # Build settings from it
        session_settings = SessionSettings(
            initial_frame=initial_frame,
            max_number_of_files=args.get('max_number_of_files', 1),
            delete_photo_after_download=args.get(
                'delete_photo_after_download', False),
            metadata=MetaData(exposure_number=None, **metadata)
        )

        # Save as last used settings
        with settings.SettingsSaver() as s:
            s.last_session_settings = session_settings

        # Create a new session
        the_session = session.get_or_new_session(
            capture_camera, the_scanner, archive_storage.photos_path,
            session_settings, post_message, exif_tag_func)
        return _get_session_details(the_session), HTTPStatus.CREATED.value


@ns.route('/session/last_used_settings/')
class SessionLastUsedSettingsResource(Resource):
    @ns.doc('get_last_used_settings')
    @ns.marshal_with(session_settings_model, code=HTTPStatus.OK.value)
    def get(self):
        """
        List of accepted values for the exposure compensation camera setting
        """
        last_used_settings = settings.get_settings().last_session_settings
        if last_used_settings is None:
            return {}

        # Transform the settings to adapt to the output format
        # First, the metadata
        metadata = last_used_settings.metadata
        output_meta = metadata.to_dict() if metadata is not None else {}
        output = {f'{METADATA_PREFIX}{k}': v for k, v in output_meta.items()}

        # Then the session settings
        output['delete_photo_after_download'] = last_used_settings.delete_photo_after_download
        output['max_number_of_files'] = last_used_settings.max_number_of_files
        # We are forced to do this manually as there's a bug with customer encodes in dataclasses-json
        output['initial_frame'] = str(last_used_settings.initial_frame)

        return output


@ns.route('/session/<int:session_id>/')
@ns.response(404, 'Session not found', error_model)
class SessionResource(Resource):
    @ns.doc('session_details')
    @ns.marshal_with(session_details, code=HTTPStatus.OK.value)
    def get(self, session_id: int):
        """
        Get session details

        :raises SessionDoesNotExist: Session not found
        """
        the_session = session.get_session(session_id)
        return _get_session_details(the_session)

    @ns.doc('skip_holes')
    @ns.expect(skip_holes_model, validate=True)
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def put(self, session_id: int):
        """
        Skip the given number of holes

        :raises SessionDoesNotExist: Session not found
        """
        the_session = session.get_session(session_id)
        number_of_holes = api.payload['number_of_holes']
        the_session.skip_holes_async(number_of_holes)
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('start_scan')
    @ns.marshal_with(status_model, code=HTTPStatus.ACCEPTED.value)
    def post(self, session_id: int):
        """
        Start scanning

        :raises SessionDoesNotExist: Session not found
        """
        the_session = session.get_session(session_id)
        the_session.start_scan_async()
        return {"success": True}, HTTPStatus.ACCEPTED.value

    @ns.doc('stop_session')
    @ns.marshal_with(status_model, code=HTTPStatus.OK.value)
    def delete(self, session_id: int):
        """
        Stop scanning and finishes the session

        :raises SessionDoesNotExist: Session not found
        """
        the_session = session.get_session(session_id)
        the_session.stop()
        return {"success": True}


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


@ns.errorhandler(camera.CameraException)
@ns.marshal_with(error_model, code=500)
def handle_camera_exception(error):
    """
    Camera error
    """
    log.error("Error with the camera", error)
    return {'message': error.message}, 500


@ns.errorhandler(SessionDoesNotExist)
@ns.marshal_with(error_model, code=404)
def handle_session_not_found(error):
    """
    Session error
    """
    log.error("Session not found", error)
    return {'message': error.message}, 404


@ns.errorhandler(Exception)
@ns.marshal_with(error_model, code=500)
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


def _get_session_details(the_session: Session):
    return {
        "id": the_session.id,
        "is_scanning": the_session.is_scanning,
        "feature_skip_hole": the_session.support_hole_skipping,
    }


def main() -> None:
    args = utils.parse_arguments()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s")

    # Storage
    archive_storage.photos_path = _ensure_path(args.destination)
    archive_storage.archive_path = _ensure_path(args.archive)
    temporary_path = _ensure_path(args.temp)

    # Initialise recently used settings
    settings.init_settings(args.settings)

    global capture_camera
    capture_camera = camera.get_camera_type(args.dryrun)(temporary_path)

    global the_scanner
    # the_scanner = scanner.Scanner(
    #     args.led, args.infrared, args.backlight, args.pin1, args.pin2, args.pin3, args.pin4)
    the_scanner = detector_scanner.DetectorScanner(
        capture_camera, args.backlight, args.pin1, args.pin2, args.pin3, args.pin4, args.use_edge_tpu)

    global exif_tag_func
    exif_tag_func = exif_tagger.async_tagger()

    # See: https://github.com/noirbizarre/flask-restplus/issues/693
    if args.verbose:
        app.config["PROPAGATE_EXCEPTIONS"] = False

    # Start web server
    socketio.run(app, host='0.0.0.0', port=args.port, debug=args.verbose)


if __name__ == "__main__":
    main()
