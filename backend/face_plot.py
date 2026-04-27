import math
from typing import Dict
import plotly.graph_objects as go


def build_face_plot(emotion_values: Dict[str, float], region_response: Dict[str, float]) -> go.Figure:
    happy = emotion_values["Happy"]
    sad = emotion_values["Sad"]
    angry = emotion_values["Angry"]
    surprise = emotion_values["Surprise"]
    disgust = emotion_values["Disgust"]
    fear = emotion_values["Fear"]

    mouth_curve = 0.55 * happy - 0.50 * sad - 0.30 * disgust
    brow_tilt = 0.40 * angry + 0.25 * fear - 0.15 * happy
    eye_open = 1.00 + 0.40 * surprise - 0.20 * sad
    jaw_open = 0.15 + 0.45 * surprise + 0.20 * fear

    t = [i / 100 for i in range(101)]

    face_x = [math.cos(2 * math.pi * v) for v in t]
    face_y = [1.18 * math.sin(2 * math.pi * v) for v in t]

    mouth_x = [-0.40 + 0.80 * v for v in t]
    mouth_y = [
        -0.45 + mouth_curve * ((x / 0.40) ** 2 - 1.0) * 0.15 - jaw_open * 0.04
        for x in mouth_x
    ]

    left_eye_x = [-0.35 + 0.12 * math.cos(2 * math.pi * v) for v in t]
    left_eye_y = [0.20 + 0.08 * eye_open * math.sin(2 * math.pi * v) for v in t]

    right_eye_x = [0.35 + 0.12 * math.cos(2 * math.pi * v) for v in t]
    right_eye_y = [0.20 + 0.08 * eye_open * math.sin(2 * math.pi * v) for v in t]

    left_brow_x = [-0.48, -0.22]
    left_brow_y = [0.45 - brow_tilt * 0.12, 0.48 + brow_tilt * 0.10]

    right_brow_x = [0.22, 0.48]
    right_brow_y = [0.48 + brow_tilt * 0.10, 0.45 - brow_tilt * 0.12]

    nose_x = [0.0, -0.05, 0.05, 0.0]
    nose_y = [0.12, -0.08, -0.08, 0.12]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=face_x, y=face_y, mode="lines", name="Face"))
    fig.add_trace(go.Scatter(x=left_eye_x, y=left_eye_y, mode="lines", name="Left Eye"))
    fig.add_trace(go.Scatter(x=right_eye_x, y=right_eye_y, mode="lines", name="Right Eye"))
    fig.add_trace(go.Scatter(x=left_brow_x, y=left_brow_y, mode="lines", name="Left Brow"))
    fig.add_trace(go.Scatter(x=right_brow_x, y=right_brow_y, mode="lines", name="Right Brow"))
    fig.add_trace(go.Scatter(x=nose_x, y=nose_y, mode="lines", name="Nose"))
    fig.add_trace(go.Scatter(x=mouth_x, y=mouth_y, mode="lines", name="Mouth"))

    fig.update_layout(
        title="Face Preview Placeholder (ready to connect to OBJ / Shape Key later)",
        showlegend=False,
        xaxis=dict(visible=False, range=[-1.3, 1.3]),
        yaxis=dict(visible=False, range=[-1.4, 1.4], scaleanchor="x", scaleratio=1),
        height=560,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig