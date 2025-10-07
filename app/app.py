from flask import Flask, request, jsonify, render_template
from match_predict import predict_match_outcome
from config import DB_CONFIG
import psycopg2

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/champions', methods=['GET'])
def get_champions():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT champion_name FROM champions ORDER BY champion_name")
        champions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(champions)
    except psycopg2.Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/roles', methods=['GET'])
def get_roles():
    roles = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']
    return jsonify(roles)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        if not data or 'blue_team' not in data or 'red_team' not in data:
            return jsonify({'status': 'error', 'message': 'Неверный формат данных: ожидаются blue_team и red_team'}), 400

        blue_team = data['blue_team']
        red_team = data['red_team']

        if len(blue_team) != 5 or len(red_team) != 5:
            return jsonify({'status': 'error', 'message': 'Каждая команда должна содержать ровно 5 игроков'}), 400

        for i, player in enumerate(blue_team + red_team, 1):
            if not all(key in player for key in ['game_name', 'tag_line', 'role', 'champion']):
                return jsonify({'status': 'error', 'message': f'Неверные данные для игрока {i}: отсутствуют обязательные поля'}), 400
            if not player['game_name'] or not player['tag_line']:
                return jsonify({'status': 'error', 'message': f'Неверные данные для игрока {i}: game_name или tag_line пусты'}), 400

        prob_blue_win = predict_match_outcome(blue_team, red_team)
        return jsonify({
            'status': 'success',
            'blue_win': round(prob_blue_win * 100, 2),
            'red_win': round((1 - prob_blue_win) * 100, 2)
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(f"Ошибка в /predict: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)