import sounddevice as sd
import soundfile as sf
import os
from PIL import Image
from werkzeug.utils import secure_filename
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from newsapi import NewsApiClient
import threading
import librosa
import numpy as np
from io import BytesIO
from tensorflow import keras

app = Flask(__name__)

# Connect to SQLite database
conn = sqlite3.connect("contact.db", check_same_thread=False)
cursor = conn.cursor()


model_path = os.path.join(os.path.dirname(__file__), 'Models', 'best_model1.h5')

# Create a table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Meddit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        content TEXT NOT NULL
    )
''')
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import Conv2D, Flatten, Dense, MaxPool2D # type: ignore
import tensorflow as tf

classes={0:('actinic keratoses and intraepithelial carcinomae(Cancer)'),
         1:('basal cell carcinoma(Cancer)'),
         2:('benign keratosis-like lesions(Non-Cancerous)'),
         3:('dermatofibroma(Non-Cancerous)'),
         4:('melanocytic nevi(Non-Cancerous)'),
         5:('pyogenic granulomas and hemorrhage(Can lead to cancer)'),
         6:('melanoma(Cancer)')}

model = Sequential()
model.add(Conv2D(16, kernel_size = (3,3), input_shape = (28, 28, 3), activation = 'relu', padding = 'same'))
model.add(MaxPool2D(pool_size = (2,2)))
model.add(tf.keras.layers.BatchNormalization())
model.add(Conv2D(32, kernel_size = (3,3), activation = 'relu'))
model.add(Conv2D(64, kernel_size = (3,3), activation = 'relu'))
model.add(MaxPool2D(pool_size = (2,2)))
model.add(tf.keras.layers.BatchNormalization())
model.add(Conv2D(128, kernel_size = (3,3), activation = 'relu'))
model.add(Conv2D(256, kernel_size = (3,3), activation = 'relu'))
model.add(Flatten())
model.add(tf.keras.layers.Dropout(0.2))
model.add(Dense(256,activation='relu'))
model.add(tf.keras.layers.BatchNormalization())
model.add(tf.keras.layers.Dropout(0.2))
model.add(Dense(128,activation='relu'))
model.add(tf.keras.layers.BatchNormalization())
model.add(Dense(64,activation='relu'))
model.add(tf.keras.layers.BatchNormalization())
model.add(tf.keras.layers.Dropout(0.2))
model.add(Dense(32,activation='relu'))
model.add(tf.keras.layers.BatchNormalization())
model.add(Dense(7,activation='softmax'))

skin_classes = ["Actinic keratosis", "Basal cell carcinoma", "Benign lichenoid keratosis", "Dermatofibroma", "Melanocytic nevus", "Pyogenic granuloma", "Melanoma"]


model.load_weights(model_path)
conn.commit()
key =os.urandom(24)
trained_model = keras.models.load_model("create_audio_classification_model.h5")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = key
@app.route("/")
def about():
    return render_template('index.html')

@app.route("/news")
def news():
    try:
        newsapi = NewsApiClient(api_key="a7c40948db6d454aa8ee3f7d5754234b")
        top_headlines = newsapi.get_top_headlines(
            category='health',
            language='en',
            country='in')

        # Extract articles
        articles = top_headlines.get('articles', [])
        length = len(articles)
        # Render the template with articles
        return render_template('news.html', articles=articles, len=length)

    except Exception as e:
        print(f"An error occurred: {e}")
        return render_template('news.html')

@app.route("/meddit", methods=['GET', 'POST'])
def meddit():
    if request.method == 'POST':
        author = request.form['author']
        content = request.form['content']
        # Insert data into database
        cursor.execute('INSERT INTO Meddit (author, content) VALUES (?, ?)', (author, content))
        conn.commit()
        return redirect(url_for('meddit'))

    # Retrieve data from database
    cursor.execute('SELECT * FROM Meddit')
    posts = cursor.fetchall()

    return render_template('meddit.html', posts=posts)

@app.route("/locator")
def locator():
    return render_template('locator.html')


# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# Function to check if the file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/skincancer', methods=['GET', 'POST'])
def skincancer():
    if request.method == 'POST':
        # Check if the file part is present in the request
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']

        # If no file is selected
        if file.filename == '':
            return 'No selected file'

        # If file is allowed, save it
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                result = predict_skin_cancer(filepath)
            except Exception as e:
                print(f"Error during recording or prediction: {str(e)}")
                return render_template('SkinCancer/error.html', message="An error occurred during audio processing.")
            return render_template("SkinCancer/result.html",prediction=result)

    return render_template('SkinCancer/skincancer.html')
# Function to predict an image
def predict_skin_cancer(image_path):

    inputimg = Image.open(image_path).resize((28, 28))
    img = np.array(inputimg).reshape(-1, 28, 28, 3)
    result = model.predict(img).tolist()
    max_prob = max(result[0])
    class_ind = result[0].index(max_prob)


    if (class_ind == 0):
        info = "Actinic keratosis also known as solar keratosis or senile keratosis are names given to intraepithelial keratinocyte dysplasia. As such they are a pre-malignant lesion or in situ squamous cell carcinomas and thus a malignant lesion."
    elif (class_ind == 1):
        info = "Basal cell carcinoma is a type of skin cancer. Basal cell carcinoma begins in the basal cells — a type of cell within the skin that produces new skin cells as old ones die off.Basal cell carcinoma often appears as a slightly transparent bump on the skin, though it can take other forms. Basal cell carcinoma occurs most often on areas of the skin that are exposed to the sun, such as your head and neck"
    elif (class_ind == 2):
        info = "Benign lichenoid keratosis (BLK) usually presents as a solitary lesion that occurs predominantly on the trunk and upper extremities in middle-aged women. The pathogenesis of BLK is unclear; however, it has been suggested that BLK may be associated with the inflammatory stage of regressing solar lentigo (SL)1"
    elif (class_ind == 3):
        info = "Dermatofibromas are small, noncancerous (benign) skin growths that can develop anywhere on the body but most often appear on the lower legs, upper arms or upper back. These nodules are common in adults but are rare in children. They can be pink, gray, red or brown in color and may change color over the years. They are firm and often feel like a stone under the skin. "
    elif (class_ind == 4):
        info = "A melanocytic nevus (also known as nevocytic nevus, nevus-cell nevus and commonly as a mole) is a type of melanocytic tumor that contains nevus cells. Some sources equate the term mole with ‘melanocytic nevus’, but there are also sources that equate the term mole with any nevus form."
    elif (class_ind == 5):
        info = "Pyogenic granulomas are skin growths that are small, round, and usually bloody red in color. They tend to bleed because they contain a large number of blood vessels. They’re also known as lobular capillary hemangioma or granuloma telangiectaticum."
    elif (class_ind == 6):
        info = "Melanoma, the most serious type of skin cancer, develops in the cells (melanocytes) that produce melanin — the pigment that gives your skin its color. Melanoma can also form in your eyes and, rarely, inside your body, such as in your nose or throat. The exact cause of all melanomas isn't clear, but exposure to ultraviolet (UV) radiation from sunlight or tanning lamps and beds increases your risk of developing melanoma."

    return info
@app.route("/contact")
def contact():
    return render_template("contact/contact.html")

@app.route("/test")
def test():
    return render_template("onlinetest/onlinetest.html")

# Handling lung cancer recording

app.config['USER_INFO_FILE'] = 'user_info.txt'

# Mapping each step to its corresponding recording duration
RECORDING_DURATIONS = {
    'Breathing Deep': 11,
    'Breathing Shallow': 8,
    'Cough Heavy': 5,
    'Cough Shallow': 5,
    'Vowel A': 8,
    'Vowel E': 8,
    'Vowel O': 8,
    'Counting Fast': 5,
    'Normal': 10
}

@app.route("/lunghealth")
def lungcancer():
    return render_template('lungcancer/lungcancer.html')


# Capture user info and redirect to recording page
@app.route('/record', methods=['POST'])
def record():
    user_info = {
        'name': request.form['name'],
        'age': request.form['age'],
        'place': request.form['place'],
        'smoking': request.form['smoking'],
        'previous_disease': request.form['previous_disease'],
        'phone': request.form['phone'],
        'email': request.form['email']
    }

    # You can process user_info here or just pass it to the result page
    return redirect(url_for('record_page'))


# Render the recording page
@app.route('/record_page')
def record_page():
    return render_template('lungcancer/record3.html', recording_durations=RECORDING_DURATIONS)


# Record audio and process it without saving to disk
@app.route('/record_audio', methods=['POST'])
def record_audio():
    audio_step = request.form['audio_step']

    # Get the corresponding recording duration for the selected step
    duration = RECORDING_DURATIONS.get(audio_step, 5)  # Default to 5 seconds if not found
    samplerate = 48000

    try:
        # Record audio in memory
        recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()

        # Save to in-memory buffer (BytesIO)
        audio_buffer = BytesIO()
        sf.write(audio_buffer, recording, samplerate, format='WAV')
        audio_buffer.seek(0)
        prediction = predict_respiratory_disease(trained_model, audio_buffer)
        return render_template('lungcancer/result.html', prediction=prediction)

    except Exception as e:
        print(f"Error during recording or prediction: {str(e)}")
        return render_template('lungcancer/error.html', message="An error occurred during audio processing.")


@app.route("/reaction")
def reaction():
    return render_template("onlinetest/reaction.html")

@app.route("/num_seq")
def num_seq():
    return render_template("onlinetest/numsequence.html")

@app.route("/verbal")
def verbal():
    return render_template("onlinetest/verbal.html")

@app.route("/skn_info")
def skn_info():
    return render_template("skn_info.html")

@app.route("/disease_info_page")
def disease_info_page():
    return render_template("lungcancer/lungcancer_info.html")


def start_gradio():
    os.system('python chatbot.py')

@app.route('/chat')
def chat():
    gradio_url = "http://127.0.0.1:7860"
    return render_template('chat.html', gradio_url=gradio_url)


def extract_audio_features(audio_signal, sr):
    try:
        # Extract audio features using librosa (e.g., chroma_stft, rmse, spectral_centroid)
        chroma_stft = librosa.feature.chroma_stft(y=audio_signal, sr=sr)
        rmse = librosa.feature.rms(y=audio_signal)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_signal, sr=sr)
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_signal, sr=sr)

        # Combine features into a single feature array
        features = np.hstack([chroma_stft.mean(axis=1), rmse.mean(), spectral_centroid.mean(), spectral_bandwidth.mean()])
        return features

    except Exception as e:
        print(f"Error extracting features from audio signal: {str(e)}")


def predict_respiratory_disease(trained_model, file):
    try:
        # Load audio from the in-memory file
        data, samplerate = sf.read(file)

        # Extract features from the audio signal
        audio_features = extract_audio_features(data, samplerate)

        if audio_features is not None:
            # Reshape the features to match the model's expected input shape
            audio_features_reshaped = audio_features.reshape(1, -1)

            # Use the trained model to make a prediction
            prediction = trained_model.predict(audio_features_reshaped)

            # Return the prediction for rendering on the result page
            return {
                'no_disease_prob': prediction[0][0] * 100,
                'disease_prob': prediction[0][1] * 100
            }

    except Exception as e:
        print(f"Error during prediction: {str(e)}")
        return {
            error:"Error Occured"
        }



if __name__ == "__main__":
    # Start Gradio server in a separate thread

    gradio_thread = threading.Thread(target=start_gradio)
    gradio_thread.start()

    # Start Flask server
    app.run(debug=True, use_reloader=False)