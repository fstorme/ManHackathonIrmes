import plotly.graph_objs as go

def create_field():
    # Création du rectangle représentant le terrain
    terrain = go.layout.Shape(
        type='rect',
        x0=0,
        y0=0,
        x1=120,
        y1=80,
        line=dict(
            color='green',
            width=2,
        ),
        fillcolor='rgba(0, 128, 0, 0.4)',
    )

    # Ajout des surfaces de réparation
    surface_reparation_gauche = go.layout.Shape(
        type='rect',
        x0=0,
        y0=30,
        x1=16.5,
        y1=50,
        line=dict(
            color='white',
            width=2,
        ),
        fillcolor='rgba(255, 255, 255, 0.4)',
    )

    surface_reparation_droite = go.layout.Shape(
        type='rect',
        x0=120-16.5,
        y0=30,
        x1=120,
        y1=50,
        line=dict(
            color='white',
            width=2,
        ),
        fillcolor='rgba(255, 255, 255, 0.4)',
    )

    # Ajout du cercle central
    cercle_central = go.layout.Shape(
        type='circle',
        x0=60-9.15,
        y0=40-9.15,
        x1=60+9.15,
        y1=40+9.15,
        line=dict(
            color='white',
            width=2,
        ),
        fillcolor='rgba(255, 255, 255, 0.4)',
    )

    # Configuration du layout du graphique
    layout = go.Layout(
        title='Terrain de football',
        shapes=[terrain, surface_reparation_gauche, surface_reparation_droite,
                cercle_central],
        xaxis=dict(
            range=[0, 120],
            dtick=20,
            title='Longueur du terrain (m)',
            ),
        yaxis=dict(
            range=[0, 80],
            dtick=20,
            title='Largeur du terrain (m)',
            ),
    )

    # Création de la figure et affichage
    fig = go.Figure(layout=layout)
    return fig
