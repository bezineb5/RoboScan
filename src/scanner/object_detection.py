from datetime import datetime
import logging
import pathlib
from typing import List, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageOps
try:
    from tensorflow import lite as tflite # First, try tensorflow
except:
    import tflite_runtime.interpreter as tflite # TensorFlow lite interpreter

log = logging.getLogger(__name__)

COLORS = ['red', 'green', 'blue', 'purple', 'yellow', 'orange']


def _load_labels(filename):
    with open(filename, 'r') as f:
        # For whatever reason, there's a "background" on the first line which is not used afterwards
        return [line.strip() for line in f.readlines()][1:]


class ObjectDetection:
    __slots__ = ['_labels', '_interpreter', 
                 '_input_size', '_input_index', 
                 '_output_boxes_index', '_output_labels_index', 
                 '_output_confidences_index', '_output_num_of_boxes_index',
                 '_color_mapping', ]

    def __init__(self, model_file: str, label_file: str, use_edge_tpu: bool = False) -> None:
        log.info("Loading model: %s", model_file)

        self._labels = _load_labels(label_file)

        experimental_delegates = [tflite.load_delegate('libedgetpu.so.1')] if use_edge_tpu else None
        self._interpreter = tflite.Interpreter(model_path=model_file, experimental_delegates=experimental_delegates)
        self._interpreter.allocate_tensors()

        # Prepare input metadata
        # NxHxWxC, H:1, W:2
        input_details = self._interpreter.get_input_details()

        shape = input_details[0]['shape']
        height = shape[1]
        width = shape[2]
        self._input_size = (width, height)
        self._input_index = input_details[0]['index']

        # Prepare output data
        output_details = self._interpreter.get_output_details()
        self._output_boxes_index = output_details[0]['index']
        self._output_labels_index = output_details[1]['index']
        self._output_confidences_index = output_details[2]['index']
        self._output_num_of_boxes_index = output_details[3]['index']

        # Initialize a color mapping
        cm = zip(self._labels, COLORS)
        self._color_mapping = {v[0]: v[1] for v in cm}
        log.info("Color mapping: %s", self._color_mapping)

    def infer_from_file(self, image_file: Union[pathlib.Path, str]) -> List[Tuple[str, np.array, float]]:
        image = Image.open(image_file)
        return self.infer(image)

    def infer(self, image: Image) -> List[Tuple[str, np.array, float]]:
        start_time = datetime.now()
        #img = ImageOps.grayscale(image)
        #img = img.resize(self._input_size).convert('RGB')
        image.draft('L', self._input_size)
        img = image.resize(self._input_size).convert('RGB')

        # add N dim
        input_data = np.expand_dims(img, axis=0)

        self._interpreter.set_tensor(self._input_index, input_data)

        mid_time = datetime.now()
        self._interpreter.invoke()
        end_time = datetime.now()
        log.info('Elapsed inference time (hh:mm:ss.ms): %s / image processing time: %s', end_time - mid_time, mid_time - start_time)

        # Bounding boxes
        output_boxes = self._interpreter.get_tensor(self._output_boxes_index)
        result_boxes = np.squeeze(output_boxes)
        # Labels
        output_labels = self._interpreter.get_tensor(self._output_labels_index)
        result_labels_indexes = np.int_(np.squeeze(output_labels))
        result_labels = [self._labels[i] for i in result_labels_indexes]
        # Confidences
        output_confidences = self._interpreter.get_tensor(self._output_confidences_index)
        result_confidences = np.squeeze(output_confidences)
        # Num of boxes
        # output_num_boxes = self._interpreter.get_tensor(self._output_num_of_boxes_index)
        # log.info("numbox: %s", np.squeeze(output_num_boxes))
        # result_num_boxes = np.int_(np.squeeze(output_num_boxes))

        return list(zip(result_labels, result_boxes, result_confidences))

    def draw_detections(self, image: Image, detections: List[Tuple[str, np.array, float]], threshold: float=0.5) -> Image:
        img = image.convert('RGB')
        width = img.size[0]
        height = img.size[1]
        draw = ImageDraw.Draw(img)

        for d in detections:
            # Label color
            label = d[0]
            color = self._color_mapping.get(label, 'black')

            # Bounding box
            bounding_box = d[1]
            y1, x1, y2, x2 = np.float_(bounding_box).tolist()
            rect = [x1 * width, y1 * height, x2 * width, y2 * height]

            # Confidence
            confidence = d[2]
            thickness = 4 if confidence >= threshold else 1

            draw.rectangle(rect, outline=color, width=thickness)

        return img
