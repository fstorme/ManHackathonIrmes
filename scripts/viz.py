import plotly.graph_objs as go

def create_field():
    # Création du rectangle représentant le terrain
    filed_color = 'rgba(31, 29, 43, 1)' 
    line_color = 'rgba(57, 60, 73, 1)'
    line_width = 3

    terrain_1 = go.layout.Shape(
        type='rect',
        x0=0,
        y0=0,
        x1=60,
        y1=80,
        line=dict(
            color=line_color,
            width=line_width,
        ),
        layer='below'
        #fillcolor=filed_color,
    )

    terrain_2 = go.layout.Shape(
        type='rect',
        x0=60,
        y0=0,
        x1=120,
        y1=80,
        line=dict(
            color=line_color,
            width=line_width,
        ),
        layer='below'
        #fillcolor=filed_color,
    )

    # Ajout des surfaces de réparation
    surface_reparation_gauche = go.layout.Shape(
        type='rect',
        x0=0,
        y0=30,
        x1=16.5,
        y1=50,
        line=dict(
            color=line_color,
            width=line_width,
        ),
        layer='below'
        #fillcolor='rgba(255, 255, 255, 0.4)',
    )

    surface_reparation_droite = go.layout.Shape(
        type='rect',
        x0=120-16.5,
        y0=30,
        x1=120,
        y1=50,
        line=dict(
            color=line_color,
            width=line_width,
        ),
        layer='below'
        #fillcolor='rgba(255, 255, 255, 0.4)',
    )

    # Ajout du cercle central
    cercle_central = go.layout.Shape(
        type='circle',
        x0=60-9.15,
        y0=40-9.15,
        x1=60+9.15,
        y1=40+9.15,
        line=dict(
            color=line_color,
            width=line_width,
        ),
        layer='below'
        #fillcolor='rgba(255, 255, 255, 0.4)',
    )

    # Configuration du layout du graphique
    layout = go.Layout(
        shapes=[terrain_1, terrain_2, surface_reparation_gauche, surface_reparation_droite,
                cercle_central]
    )

    # Création de la figure et affichage
    fig = go.Figure(layout=layout)
    return fig
