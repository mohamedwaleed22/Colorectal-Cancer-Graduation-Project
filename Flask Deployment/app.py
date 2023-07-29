from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from keras.models import load_model
import tensorflow_hub as hub
import numpy as np
from tensorflow.keras.preprocessing import image
import os
import tensorflow as tf
import io
import requests
from flask import Flask, request, jsonify
from tensorflow.keras.utils import img_to_array
import cv2
from ultralytics import YOLO
from genes import func

app = Flask(__name__)
cors =  CORS(app, resources={r"/*": {"origins": "*"}})
if __name__ == '__main__':
    app.run()


def load_image(img_path):
    full_path = os.path.join('out', img_path)
    img = image.load_img(full_path, target_size=(299, 299))
    img_tensor = image.img_to_array(img)
    img_tensor = np.expand_dims(img_tensor, axis=0)
    img_tensor /= 255
    return img_tensor



##########################################################################
# this for gene expression


@app.route('/gene_search', methods=['POST'])
def gene_search():
    user_input = request.json['gene']
    result = func(user_input)
    return jsonify(result)


##########################################################################
# histopathology model


@app.route('/histopathology/predict', methods=['POST'])
def histo():
    file = request.files['image']
    path = './histo_class_final.h5'
    custom_objects = {'KerasLayer': hub.KerasLayer}
    with tf.device('/cpu:0'):
        model = tf.keras.models.load_model(path, custom_objects=custom_objects)
    if not os.path.exists('out'):
        os.makedirs('out')
    file.save(os.path.join('out', file.filename))
    img = load_image(file.filename)
    prediction = model.predict(img)
    classes = np.argmax(prediction, axis=1)[0]
    if classes == 0:
        return jsonify("Adenocarcinoma (Cancerous)")
    elif classes == 1:
        return jsonify("Benign (Non Cancerous)")
    else:
        return jsonify("False data entry")

##########################################################################
# endoscopy  route


@app.route('/endoscopy/predict/2', methods=['POST'])
def endo_class():
    if request.method != "POST":
        return jsonify("Invalid request method")

    try:
        if request.files.get("image"):
            file = request.files['image']
            file.save(os.path.join('out', file.filename))
            # load the image

            folder_path = os.path.abspath(file.filename)
            print(folder_path)
            print(file.filename)
            image = cv2.imread("{}models\\out\\{}".format(
                folder_path.split("models")[0], file.filename))
            image = cv2.resize(image, (28, 28))

    except Exception as e:
        return jsonify("Please select another image")

    if not os.path.exists('out'):
        os.makedirs('out')

    image = image.astype("float") / 255.0
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0)

    # load the model
    model = load_model('./mynet2.model')

    # classify the input image
    (Malignant, Benign) = model.predict(image)[0]

    # build the label
    label1 = "Hyperplastic" if Benign > Malignant else "Adenomatous"
    proba = Benign if Benign > Malignant else Malignant
    label = "{}: {:.2f}%".format(label1, proba * 100)
    bin_label = 0 if label1 == "Hyperplastic" else 1

    return jsonify([{"to_image": label, "label_binary": bin_label}])

##########################################################################


@app.route('/endoscopy/predict', methods=['POST'])
def endoscopy_predict():
    file = request.files['image']
    path = './endo_model_class.h5'
    custom_objects = {'KerasLayer': hub.KerasLayer}
    with tf.device('/cpu:0'):
        model = load_model(path, custom_objects=custom_objects)
    if not os.path.exists('out'):
        os.makedirs('out')
    file.save(os.path.join('out', file.filename))
    img = load_image(file.filename)
    prediction = model.predict(img)
    classes_x = np.argmax(prediction, axis=1)
    classes = classes_x[0]
    if classes == 0:
        image_data = open(os.path.join('out', file.filename), 'rb').read()
        files = {'image': ('out.jpg', image_data, 'image/jpeg')}
        try:
            response = requests.post(
                'http://localhost:5000/endoscopy/predict/2', files=files)
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return jsonify("Invalid response from /endoscopy/predict/2 route")
    else:
        false_data = [{'error': 'False data entry'}]
        return jsonify(false_data)

    #########################################################################


model_adeno = YOLO("./best_adeno_M_416.pt")


@app.route('/adeno', methods=["POST"])
def yolo_Adeno():
    if request.method != "POST":
        return jsonify("Invalid request method")

    if request.files.get("image"):
        image_file = request.files["image"]
        image_bytes = image_file.read()
        img = Image.open(io.BytesIO(image_bytes))
        resized_image = img.resize((416, 416))

        results = model_adeno(resized_image)

        if len(results) > 0:
            class_name = results[0].names
            clss = class_name[0]
            boxes = results[0].boxes
            if len(boxes) > 0:
                box = boxes[0]
                confidence = box.conf
                conf = float(confidence.item())
                bbox = box.xyxy
                bbox_list = bbox.tolist()[0]

                return jsonify([{'class_name': clss, 'conf': conf, 'bbox_list': bbox_list}])

        return jsonify("No results found")

    return jsonify("No image file provided")

#########################################################################


model_hyper = YOLO("./best_hyper_M_416.pt")


@app.route('/hyper', methods=["POST"])
def yolo_Hyper():
    if request.method != "POST":
        return jsonify("Invalid request method")

    if request.files.get("image"):
        image_file = request.files["image"]
        image_bytes = image_file.read()
        img = Image.open(io.BytesIO(image_bytes))
        resized_image = img.resize((416, 416))

        results = model_hyper(resized_image)

        if len(results) > 0:
            class_name = results[0].names
            clss = class_name[0]
            boxes = results[0].boxes
            if len(boxes) > 0:
                box = boxes[0]
                confidence = box.conf
                conf = float(confidence.item())
                bbox = box.xyxy
                bbox_list = bbox.tolist()[0]

                return jsonify([{'class_name': clss, 'conf': conf, 'bbox_list': bbox_list}])

        return jsonify("No results found")

    return jsonify("No image file provided")


