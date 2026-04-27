from typing import List
import plotly.graph_objects as go


def build_mesh_figure(
    vertices: List[List[float]],
    faces: List[List[int]],
    title: str = "OBJ 3D Model Preview",
) -> go.Figure:
    """
    使用 Plotly 显示 3D 网格模型。
    """
    if not vertices:
        fig = go.Figure()
        fig.update_layout(
            title="No mesh data",
            height=560,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        return fig

    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]

    if faces:
        i = [f[0] for f in faces]
        j = [f[1] for f in faces]
        k = [f[2] for f in faces]

        fig = go.Figure(
            data=[
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    i=i,
                    j=j,
                    k=k,
                    opacity=1.0,
                )
            ]
        )
    else:
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode="markers",
                )
            ]
        )

    fig.update_layout(
        title=title,
        height=560,
        margin=dict(l=10, r=10, t=50, b=10),
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="data",
        ),
    )

    return fig