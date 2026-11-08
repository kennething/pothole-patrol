<!-- <img src="./frontend/public/sprites/chicken/hehe.webp" height="100" /> -->

# Pothole Patrol - NYCAIRR Hackathon Submission

Created by Kenneth Ng, Tiffany Lin, and Ryan Zhou for the NYCAIRR Hackathon.

## Program Purpose

Pothole Patrol uses cameras that are already on the road to detect potholes in
real-time and share the data with cities and governments to help them prioritize
road repairs. After seeing the viral posts about Mayor Mamdani fixing potholes
in New York City, we wanted to create a solution to help cities like New York
City detect (and hopefully fix) more potholes than ever.

## Program Functionality

Users connect with the camera frontend to continuously poll and stream video
from their cameras to the WebSocket server. This camera serves as a stand-in for
a dashcam or any other type of camera that travels on the road.

The WebSocket server recieves the video stream and forwards it, along with extra
metadata used later in the process for calculations, to the model backend via
gRPC.

The model backend uses a YOLOv8 model to detect potholes in the video stream.
Then, if a pothole is detected, several other information points are fetched and
calculated, including, but not limited to:

- Average income areas
- Population of the area
- Severity of the pothole

Then, the model backend sends the data to the API backend via a persistent
unidirectional gRPC stream. The API server stores the data in a PostgreSQL
database and serves it to the dashboard frontend via a standard REST API.

Other users can now connect to the dashboard frontend to view pothole data in
real-time, including a map of potholes and a recommended repair priority list
based on the data collected and our algorithms.

## Our Tech Stack

We used a microservice architecture philosophy to build our application, with
each component being able to be scaled independently for different workloads.
The following technologies were used to build our application:

- Nuxt.js (Vue) for the camera frontend
- Express.js + Socket.IO for the WebSocket server
- YOLOv8 + PyTorch for the model backend
- Rocket.rs + PostgreSQL for the API backend
- Next.js (React) + Tauri for the dashboard frontend app

- gRPC for inter-server communication
- WebSockets for communication between camera and WebSocket server
- REST API for communication between dashboard frontend and API backend

## Known Limitations

- Detection currently runs on the stock COCO-trained `yolov8n` checkpoint, not a
  pothole-trained one, so the detection gate flags any recognized object rather
  than potholes specifically.
- Pothole severity comes from a `res2net50d` bounding-box regressor
  (`model/server/length_of_pothole.pt`) converted to a 0-100 score through an
  uncalibrated pinhole-camera model. It is a consistent relative ranking across
  frames from the same camera, not a true physical measurement. Calibrate
  `FOCAL_PX` and `CAMERA_DISTANCE_CM` per camera for real-world lengths.
- `area_transit_ridership`, `area_gdp` and `area_commercial` have no data source
  yet and are always reported as 0.

## AI Usage

AI was used to debug parts of our code.
