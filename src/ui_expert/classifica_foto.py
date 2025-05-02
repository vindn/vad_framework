from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Estrutura de dados atualizada com informações adicionais
trajetorias = [
    [
        {'coords': (37.7749, -122.4194), 'info': {'nome': 'Ponto 1', 'direcao': 'Norte', 'velocidade': '60km/h'}},
        {'coords': (34.0522, -118.2437), 'info': {'nome': 'Ponto 2', 'direcao': 'Leste', 'velocidade': '65km/h'}},
        {'coords': (36.1699, -115.1398), 'info': {'nome': 'Ponto 3', 'direcao': 'Sul', 'velocidade': '70km/h'}}
    ],
    [
        {'coords': (37.7749, -122.4194), 'info': {'nome': 'Ponto K', 'direcao': 'Norte', 'velocidade': '60km/h'}},
        {'coords': (34.0522, -118.2437), 'info': {'nome': 'Ponto K', 'direcao': 'Leste', 'velocidade': '65km/h'}},
        {'coords': (36.1699, -115.1398), 'info': {'nome': 'Ponto K', 'direcao': 'Sul', 'velocidade': '70km/h'}}
    ],    
    # Mais trajetórias...
]

@app.route('/')
@app.route('/<int:trajetoria_id>')
def index(trajetoria_id=0):
    if trajetoria_id >= len(trajetorias):
        return "Todas as trajetórias foram classificadas!"
    trajetoria_atual = trajetorias[trajetoria_id]
    return render_template('index.html', trajetoria_atual=trajetoria_atual, trajetoria_id=trajetoria_id)

@app.route('/classificar/<int:trajetoria_id>', methods=['POST'])
def classificar(trajetoria_id):
    classificacao = request.form.get('classificacao')
    print(f"Trajetória {trajetoria_id} classificada como: {classificacao}")
    return redirect(url_for('index', trajetoria_id=trajetoria_id + 1))

if __name__ == '__main__':
    app.run(debug=True)
