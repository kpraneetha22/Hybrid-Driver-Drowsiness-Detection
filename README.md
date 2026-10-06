\# Hybrid Driver Drowsiness Detection



This is my final-year project on detecting driver drowsiness using computer vision and deep learning.



The main idea is to monitor the driver's face through a webcam and identify signs such as prolonged eye closure and yawning. If drowsiness is detected, the system provides an alert to get the driver's attention.



\## What does the project do?



The project uses two main approaches for detecting drowsiness:



1\. \*\*Eye closure detection\*\* using facial landmarks and Eye Aspect Ratio (EAR)

2\. \*\*Yawning detection\*\* using an Xception-based deep learning model



These are combined to make the drowsiness detection more reliable than depending on only one sign.



\## How it works



The basic flow of the project is:



```text

Webcam

&#x20;  ↓

Capture video frames

&#x20;  ↓

Detect face

&#x20;  ↓

Find facial landmarks using MediaPipe

&#x20;  ↓

&#x20;┌─────────────────────┐

&#x20;│                     │

&#x20;▼                     ▼

Eye analysis       Yawning detection

&#x20;  │                     │

&#x20;  ▼                     ▼

&#x20;EAR calculation    Xception model

&#x20;  │                     │

&#x20;  └──────────┬──────────┘

&#x20;             ↓

&#x20;      Drowsiness check

&#x20;             ↓

&#x20;           Alert

```



\### Eye closure detection



MediaPipe Face Mesh is used to identify the points around the eyes. These points are used to calculate the \*\*Eye Aspect Ratio (EAR)\*\*.



When the eyes remain closed for a certain period, the system treats it as a possible sign of drowsiness.



\### Yawning detection



For yawning detection, I used an \*\*Xception-based model\*\* trained to identify yawning from facial images.



The model is used along with the eye-closure analysis rather than using it as the only method of detection.



\## Technologies Used



\* Python

\* OpenCV

\* MediaPipe

\* NumPy

\* SciPy

\* TensorFlow / Keras

\* Xception

\* Flask

\* HTML / CSS

\* Jupyter Notebook



\## Project Files



```text

Hybrid-Driver-Drowsiness-Detection/

│

├── main.py

├── app.py

├── drowsiness\_yawning.ipynb

├── haarcascade\_frontalface\_default.xml

├── requirements.txt

│

├── templates/

│   ├── home.html

│   └── detect.html

│

└── .gitignore

```



\### About the files



\* `main.py` – main Python implementation

\* `app.py` – Flask application

\* `drowsiness\_yawning.ipynb` – notebook used for the yawning-detection/model work

\* `haarcascade\_frontalface\_default.xml` – Haar Cascade file used by the project

\* `templates/` – HTML pages for the web interface

\* `requirements.txt` – Python dependencies



\## Running the Project



I recommend using \*\*Python 3.11\*\* for this project because some of the computer-vision libraries used by the project have better compatibility with this version.



First clone the repository:



```bash

git clone https://github.com/kpraneetha22/Hybrid-Driver-Drowsiness-Detection.git

```



Move into the project folder:



```bash

cd Hybrid-Driver-Drowsiness-Detection

```



Create a virtual environment:



```bash

python -m venv venv

```



Activate it on Windows:



```powershell

.\\venv\\Scripts\\Activate.ps1

```



Install the required packages:



```bash

pip install -r requirements.txt

```



Then run:



```bash

python main.py

```



For the Flask interface:



```bash

python app.py

```



\## Model File



The trained Xception model is not included in this repository because of its large file size.



The model file needs to be placed in the appropriate project location before running the part of the application that uses it.



\## Why I built this



Driver drowsiness is something that can be difficult to identify before it becomes dangerous. I wanted to work on a project where computer vision could be used for something more practical than just image classification.



Through this project, I worked with facial landmarks, OpenCV, image processing, deep learning, and a Flask-based interface.



\## Limitations



This is an academic project and is not intended to be used as a certified vehicle safety system.



The detection can be affected by things such as:



\* Poor lighting

\* Camera position

\* Face occlusion

\* Wearing glasses

\* Camera quality

\* Changes in the driver's position



\## Future Improvements



Some improvements I would like to work on are:



\* Better performance in different lighting conditions

\* Improved detection when the driver is wearing glasses

\* Head-pose and gaze detection

\* Better real-time performance

\* Testing with a larger and more varied dataset

\* Deployment on an edge device or mobile platform



\## Author



\*\*Kramadhati Naga Praneetha\*\*



B.Tech – Computer Science and Engineering



GitHub: https://github.com/kpraneetha22



