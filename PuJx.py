#!/usr/bin/env python3
"""
ASD Complete System - TEACCH Schedule with Full Dashboard Integration
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import random
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'asd_complete_key'

DATA_DIR = '/home/lamya/Desktop/ASD_Complete_Project_20260325_161142/data'
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== قائمة الألعاب (من مجلد games فقط) ====================
games_dir = os.path.join(os.path.dirname(__file__), 'templates', 'games')
exclude = {'landing', 'parent_login', 'parent_register', 'child_login', 'games_menu', 'parent_dashboard', 'index'}

GAMES_LIST = []
if os.path.exists(games_dir):
    for f in os.listdir(games_dir):
        if f.endswith('.html') and os.path.splitext(f)[0] not in exclude:
            GAMES_LIST.append(os.path.splitext(f)[0])
GAMES_LIST = list(set(GAMES_LIST))  # إزالة أي تكرار
GAMES_LIST.sort()

print(f"✅ تم تحميل {len(GAMES_LIST)} لعبة")

# أيقونات مميزة لكل لعبة
ICONS = {
    'aba_matching': '🎯', 'aba_sorting': '📊', 'alphabet_song': '🎵', 'animal_sounds': '🐶',
    'ball_sort_perfect': '⚾', 'block_blast': '🧩', 'brain_oddone': '🤔', 'brain_pattern': '🔄',
    'color_match': '🎨', 'coloring_game': '🖍️', 'crossword_english': '📝', 'daily_routine': '⏰',
    'do_dont': '✅', 'drawing_pad': '✏️', 'emotion_match': '😊', 'familiar_things': '🏠',
    'language_game': '💬', 'letter_coloring': '🔤', 'math_challenge': '🔢', 'memory_cards': '🎴',
    'memory_game': '🧠', 'music_rhythm': '🎵', 'pepper_emotions': '😊', 'pepper_imitation': '🤖',
    'physical_activity': '🏃', 'sensory_bubbles': '🫧', 'sensory_fireworks': '🎆', 'sensory_spinner': '🌀',
    'shape_sorting': '⭐', 'smart_alarm': '⏰', 'snake_game': '🐍', 'social_stories_english': '📖',
    'spot_difference': '🔍', 'story_library_full': '📚', 'sudoku': '🔢', 'teacch_schedule': '📋',
    'teacch_work': '⚙️', 'tictactoe_game': '❌', 'word_search': '🔍', 'work_system': '🔧',
    'color_sort': '🎨', 'counting': '🔢'
}

# ==================== البيانات ====================
users_file = os.path.join(DATA_DIR, 'users.json')
progress_file = os.path.join(DATA_DIR, 'progress.json')
therapy_file = os.path.join(DATA_DIR, 'therapy.json')
sessions_file = os.path.join(DATA_DIR, 'sessions.json')
child_state_file = os.path.join(DATA_DIR, 'child_state.json')
teacch_file = os.path.join(DATA_DIR, 'teacch.json')

def load_json(f):
    if os.path.exists(f):
        with open(f, 'r') as fp:
            return json.load(fp)
    return {}

def save_json(f, data):
    with open(f, 'w') as fp:
        json.dump(data, fp, indent=2)

def init_child(child, age):
    prog = load_json(progress_file)
    if child not in prog:
        prog[child] = {'age': age, 'games': {}}
        for g in GAMES_LIST:
            prog[child]['games'][g] = {'played':0, 'correct':0, 'wrong':0, 'score':0, 'accuracy':0}
        save_json(progress_file, prog)
    
    therapy = load_json(therapy_file)
    if child not in therapy:
        therapy[child] = {
            'aba_stats': {'positive':0, 'calming':0, 'instructions':0},
            'attention_history': [0.5],
            'emotion_history': ['neutral'],
            'behaviour_history': ['normal'],
            'teacch_completed': []
        }
        save_json(therapy_file, therapy)
    
    sessions = load_json(sessions_file)
    if child not in sessions:
        sessions[child] = []
        save_json(sessions_file, sessions)
    
    state = load_json(child_state_file)
    if child not in state:
        state[child] = {'emotion': 'neutral', 'attention': 0.5, 'behaviour': 'normal', 'arousal': 0.5}
        save_json(child_state_file, state)
    
    teacch = load_json(teacch_file)
    if child not in teacch:
        teacch[child] = {'schedule': [], 'completed': []}
        save_json(teacch_file, teacch)

# ==================== Routes ====================
@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/parent/login', methods=['GET', 'POST'])
def parent_login():
    if request.method == 'POST':
        users = load_json(users_file)
        u = request.form['username']
        p = request.form['password']
        if u in users.get('parents', {}) and users['parents'][u]['password'] == p:
            session['user_type'] = 'parent'
            session['username'] = u
            return redirect(url_for('parent_dashboard'))
        return render_template('parent_login.html', error='Invalid')
    return render_template('parent_login.html')

@app.route('/parent/register', methods=['GET', 'POST'])
def parent_register():
    if request.method == 'POST':
        users = load_json(users_file)
        u = request.form['username']
        if u in users.get('parents', {}):
            return render_template('parent_register.html', error='Exists')
        users.setdefault('parents', {})[u] = {
            'password': request.form['password'],
            'email': request.form['email'],
            'children': []
        }
        save_json(users_file, users)
        return redirect(url_for('parent_login'))
    return render_template('parent_register.html')

@app.route('/child/login', methods=['GET', 'POST'])
def child_login():
    if request.method == 'POST':
        name = request.form['child_name']
        age = request.form['child_age']
        session['user_type'] = 'child'
        session['child_name'] = name
        session['child_age'] = age
        init_child(name, age)
        
        sessions = load_json(sessions_file)
        sessions[name].append({
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'games_played': []
        })
        save_json(sessions_file, sessions)
        
        return redirect(url_for('games_menu'))
    return render_template('child_login.html')

@app.route('/parent/dashboard')
def parent_dashboard():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    return render_template('parent_dashboard.html', games_list=GAMES_LIST, icons=ICONS)

@app.route('/games')
def games_menu():
    if 'user_type' not in session or session['user_type'] != 'child':
        return redirect(url_for('child_login'))
    return render_template('games_menu.html', games=GAMES_LIST, icons=ICONS, child_name=session['child_name'])

@app.route('/game/<game_id>')
def play_game(game_id):
    if 'user_type' not in session or session['user_type'] != 'child':
        return redirect(url_for('child_login'))
    if game_id not in GAMES_LIST:
        return "Game not found", 404
    
    child = session['child_name']
    sessions = load_json(sessions_file)
    if sessions[child]:
        sessions[child][-1]['games_played'].append({
            'game': game_id,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'correct': 0,
            'wrong': 0,
            'score': 0
        })
        save_json(sessions_file, sessions)
    
    return render_template(f'games/{game_id}.html', game={'id': game_id, 'name': game_id.replace('_', ' ').title()}, child_name=session['child_name'])

# ==================== APIs ====================
@app.route('/api/children')
def api_children():
    users = load_json(users_file)
    parent = users['parents'].get(session.get('username', ''), {})
    children = parent.get('children', [])
    prog = load_json(progress_file)
    return jsonify([{'name': c, 'age': prog.get(c, {}).get('age', '?'), 'games_played': sum(g.get('played',0) for g in prog.get(c,{}).get('games',{}).values())} for c in children])

@app.route('/api/add-child', methods=['POST'])
def api_add_child():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    name, age = data['name'], data['age']
    users = load_json(users_file)
    parent = users['parents'].get(session['username'], {})
    if 'children' not in parent:
        parent['children'] = []
    if name not in parent['children']:
        parent['children'].append(name)
        users['parents'][session['username']] = parent
        save_json(users_file, users)
        init_child(name, age)
    return jsonify({'status': 'success'})

@app.route('/api/child-progress/<child_name>')
def api_child_progress(child_name):
    prog = load_json(progress_file)
    therapy = load_json(therapy_file)
    if child_name not in prog:
        return jsonify({'games': {}, 'total': {}})
    games = prog[child_name]['games']
    total_correct = sum(g.get('correct',0) for g in games.values())
    total_wrong = sum(g.get('wrong',0) for g in games.values())
    total_score = sum(g.get('score',0) for g in games.values())
    total_games = sum(g.get('played',0) for g in games.values())
    accuracy = (total_correct/(total_correct+total_wrong)*100) if (total_correct+total_wrong)>0 else 0
    return jsonify({
        'games': games,
        'total': {'correct': total_correct, 'wrong': total_wrong, 'score': total_score, 'games_played': total_games, 'accuracy': accuracy},
        'therapy': therapy.get(child_name, {}),
        'age': prog[child_name].get('age', '?')
    })

@app.route('/api/submit-score', methods=['POST'])
def api_submit_score():
    data = request.json
    child = data['child_name']
    game_id = data['game_id']
    correct = data.get('correct', 0)
    wrong = data.get('wrong', 0)
    score = data.get('score', 0)
    
    prog = load_json(progress_file)
    if child not in prog:
        return jsonify({'status': 'error'}), 400
    if game_id not in prog[child]['games']:
        prog[child]['games'][game_id] = {'played':0, 'correct':0, 'wrong':0, 'score':0, 'accuracy':0}
    
    g = prog[child]['games'][game_id]
    if correct > 0 or wrong > 0:
        g['played'] += 1
    g['correct'] += correct
    g['wrong'] += wrong
    g['score'] += score
    total = g['correct'] + g['wrong']
    g['accuracy'] = (g['correct']/total*100) if total>0 else 0
    save_json(progress_file, prog)
    
    sessions = load_json(sessions_file)
    if child in sessions and sessions[child]:
        current_session = sessions[child][-1]
        for game in current_session.get('games_played', []):
            if game.get('game') == game_id and game.get('end_time') is None:
                game['end_time'] = datetime.now().isoformat()
                game['correct'] = correct
                game['wrong'] = wrong
                game['score'] = score
                break
        save_json(sessions_file, sessions)
        
        # Update child state based on performance
        state = load_json(child_state_file)
        if child not in state:
            state[child] = {'emotion': 'neutral', 'attention': 0.5, 'behaviour': 'normal', 'streak': 0, 'arousal': 0.5}
        
        state[child]['streak'] = state[child].get('streak', 0) + correct - wrong * 2
        
        if correct > 0:
            state[child]['attention'] = min(1.0, state[child].get('attention', 0.5) + 0.1)
            state[child]['arousal'] = min(1.0, state[child].get('arousal', 0.5) + 0.05)
            if state[child]['streak'] >= 3:
                state[child]['emotion'] = 'happy'
            else:
                state[child]['emotion'] = 'excited'
        else:
            state[child]['attention'] = max(0.0, state[child].get('attention', 0.5) - 0.05)
            state[child]['streak'] = max(0, state[child]['streak'] - 1)
            state[child]['emotion'] = 'frustrated'
        
        # Update behaviour based on attention/arousal
        attn = state[child]['attention']
        arousal = state[child]['arousal']
        if attn > 0.8 and arousal < 0.7:
            state[child]['behaviour'] = 'focused'
        elif attn < 0.3 or arousal > 0.9:
            state[child]['behaviour'] = 'distracted'
        else:
            state[child]['behaviour'] = 'normal'
        
        save_json(child_state_file, state)
    
    return jsonify({'status': 'success', 'accuracy': g['accuracy']})

@app.route('/api/therapy-action', methods=['POST'])
def api_therapy_action():
    data = request.json
    child = data['child']
    action = data['action']
    therapy = load_json(therapy_file)
    if child not in therapy:
        therapy[child] = {'aba_stats': {'positive':0,'calming':0,'instructions':0}, 'attention_history':[0.5], 'emotion_history':['neutral']}
    if action == 'positive_reinforcement':
        therapy[child]['aba_stats']['positive'] += 1
    elif action == 'calming':
        therapy[child]['aba_stats']['calming'] += 1
    elif action == 'instruction':
        therapy[child]['aba_stats']['instructions'] += 1
    save_json(therapy_file, therapy)
    return jsonify({'status': 'success'})

# ==================== TEACCH System ====================
@app.route('/api/teacch/<child_name>', methods=['GET', 'POST'])
def api_teacch(child_name):
    teacch = load_json(teacch_file)
    if child_name not in teacch:
        teacch[child_name] = {'schedule': [], 'completed': []}
    
    if request.method == 'POST':
        data = request.json
        task = data.get('task')
        task_time = data.get('time', datetime.now().strftime('%H:%M'))
        if task:
            new_task = {
                'id': len(teacch[child_name]['schedule']) + 1,
                'task': task,
                'time': task_time,
                'day': data.get('day', 'Monday'),
                'completed': False,
                'completed_time': None,
                'created_at': datetime.now().isoformat()
            }
            teacch[child_name]['schedule'].append(new_task)
            save_json(teacch_file, teacch)
            return jsonify({'status': 'success', 'task': new_task})
    
    return jsonify(teacch[child_name].get('schedule', []))

@app.route('/api/teacch/complete/<child_name>/<int:task_id>', methods=['POST'])
def api_teacch_complete(child_name, task_id):
    teacch = load_json(teacch_file)
    therapy = load_json(therapy_file)
    
    if child_name in teacch:
        for task in teacch[child_name].get('schedule', []):
            if task.get('id') == task_id and not task.get('completed', False):
                task['completed'] = True
                task['completed_time'] = datetime.now().isoformat()
                save_json(teacch_file, teacch)
                
                if child_name not in therapy:
                    therapy[child_name] = {}
                if 'teacch_completed' not in therapy[child_name]:
                    therapy[child_name]['teacch_completed'] = []
                therapy[child_name]['teacch_completed'].append({
                    'task': task.get('task'),
                    'time': task.get('time'),
                    'day': task.get('day', 'Monday'),
                    'completed_time': task['completed_time']
                })
                save_json(therapy_file, therapy)
                return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 404

@app.route('/api/teacch/completed/<child_name>', methods=['GET'])
def api_teacch_completed(child_name):
    therapy = load_json(therapy_file)
    completed = therapy.get(child_name, {}).get('teacch_completed', [])
    return jsonify(completed)

@app.route('/api/teacch/notifications/<child_name>', methods=['GET'])
def api_teacch_notifications(child_name):
    teacch = load_json(teacch_file)
    schedule = teacch.get(child_name, {}).get('schedule', [])
    current_time = datetime.now().strftime('%H:%M')
    notifications = [t for t in schedule if not t.get('completed', False) and t.get('time') == current_time]
    return jsonify(notifications)

# ==================== Child State APIs ====================
@app.route('/api/child-state/<child_name>')
def api_child_state(child_name):
    state = load_json(child_state_file)
    if child_name not in state:
        return jsonify({'emotion': 'neutral', 'attention': 0.5, 'arousal': 0.5, 'behaviour': 'normal'})
    return jsonify(state[child_name])

@app.route('/api/child-state-history/<child_name>')
def api_child_state_history(child_name):
    therapy = load_json(therapy_file)
    if child_name not in therapy:
        return jsonify({'attention_history': [0.5], 'emotion_history': ['neutral']})
    return jsonify({
        'attention_history': therapy[child_name].get('attention_history', [0.5]),
        'emotion_history': therapy[child_name].get('emotion_history', ['neutral'])
    })

@app.route('/api/sessions/<child_name>')
def api_sessions(child_name):
    sessions = load_json(sessions_file)
    return jsonify(sessions.get(child_name, []))

@app.route('/api/detect-emotion', methods=['POST'])
def api_detect_emotion():
    data = request.json
    child = data.get('child')
    emotions = ['happy', 'sad', 'neutral', 'excited', 'frustrated', 'calm']
    detected_emotion = random.choice(emotions)
    
    state = load_json(child_state_file)
    if child in state:
        state[child]['emotion'] = detected_emotion
        save_json(child_state_file, state)
        
        therapy = load_json(therapy_file)
        if child in therapy:
            therapy[child]['emotion_history'].append(detected_emotion)
            save_json(therapy_file, therapy)
    
    return jsonify({'emotion': detected_emotion})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 ASD COMPLETE SYSTEM with TEACCH")
    print("="*60)
    print(f"📍 Parent Dashboard: http://localhost:5001")
    print(f"📍 Child Games: http://localhost:5001/child/login")
    print(f"📍 Games Available: {len(GAMES_LIST)}")
    print("="*60)
    app.run(host='0.0.0.0', port=5001, debug=True)
