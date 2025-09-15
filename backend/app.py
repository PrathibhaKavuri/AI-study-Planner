import os
from flask import Flask, render_template, request, jsonify, send_file
from gemini_client import GeminiClient
import models
import io
import csv
from datetime import datetime

app = Flask(__name__, template_folder='../templates')
client = GeminiClient()
models.init_db()


@app.route('/')
def index():
    chat_history = models.get_chat_history()
    tasks = models.get_tasks()
    stats = models.get_stats()
    return render_template('index.html', chat_history=chat_history, tasks=tasks, stats=stats)


@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.get_json(silent=True) or {}
    user_message = payload.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        models.save_chat("user", user_message)
        response_text = client.generate_response(user_message)
        models.save_chat("agent", response_text)
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': f'Error generating response: {e}'}), 500


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    tasks = models.get_tasks()
    return jsonify([
        {
            "id": t[0],
            "subject": t[1],
            "description": t[2],
            "deadline": t[3],
            "completed": bool(t[4]),
            "category": t[5],
            "priority": t[6],
            "created_at": t[7]
        }
        for t in tasks
    ])


@app.route('/api/tasks', methods=['POST'])
def add_task():
    payload = request.get_json(silent=True) or {}
    subject = payload.get('subject')
    description = payload.get('description', '')
    deadline = payload.get('deadline', '')
    category = payload.get('category', 'General')
    priority = payload.get('priority', 'Medium')

    if not subject:
        return jsonify({"error": "Subject is required"}), 400

    models.add_task(subject, description, deadline, category, priority)
    return jsonify({"message": "Task added successfully"})


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def edit_task(task_id):
    payload = request.get_json(silent=True) or {}
    subject = payload.get('subject')
    description = payload.get('description', '')
    deadline = payload.get('deadline', '')
    category = payload.get('category', 'General')
    priority = payload.get('priority', 'Medium')
    completed = payload.get('completed')

    models.update_task(task_id, subject, description, deadline, category, priority, completed)
    return jsonify({"message": "Task updated"})


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    models.delete_task(task_id)
    return jsonify({"message": "Task deleted"})


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    models.mark_task_complete(task_id)
    return jsonify({"message": "Task marked complete"})


@app.route('/api/tasks/<int:task_id>/uncomplete', methods=['POST'])
def uncomplete_task(task_id):
    models.mark_task_incomplete(task_id)
    return jsonify({"message": "Task marked incomplete"})


@app.route('/api/generate-plan', methods=['GET'])
def generate_plan():
    tasks = models.get_tasks()
    if not tasks:
        return jsonify({"plan": "No tasks available to generate a study plan."})

    days_left = None
    today = datetime.today().date()

    for t in tasks:
        if t[3]:
            try:
                deadline = datetime.strptime(t[3], "%Y-%m-%d").date()
                diff = (deadline - today).days
                if diff >= 0:
                    days_left = diff if days_left is None else min(days_left, diff)
            except ValueError:
                continue

    days_left = 7 if days_left is None else max(1, days_left + 1)

    task_text = "\n".join([
        f"- {t[1]}: {t[2]} (Deadline: {t[3] or 'N/A'}) [{'Done' if t[4] else 'Pending'}]"
        for t in tasks
    ])

    prompt = (
        f"You are a helpful study planner AI. Based on the following tasks, "
        f"generate a structured {days_left}-day study schedule that ensures completion before deadlines. "
        f"Distribute work across the {days_left} days, balancing topics to avoid overload.\n\n"
        f"Tasks:\n{task_text}"
    )

    response = client.generate_response(prompt)
    models.save_chat("agent", f"[Generated {days_left}-Day Study Plan]\n" + response)

    return jsonify({"plan": response})


@app.route('/api/tasks/<int:task_id>/suggest-subtasks', methods=['POST'])
def suggest_subtasks(task_id):
    task = models.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    subject = task[1]
    description = task[2] or ''
    prompt = (
        f"Break down this study task into clear, actionable subtasks and estimated times:\n\n"
        f"Task: {subject}\nDescription: {description}\n\n"
        "Return a markdown list of subtasks with estimated durations (e.g. - Revise Chapter 1 — 45 mins)."
    )

    try:
        response = client.generate_response(prompt)
        models.save_chat("agent", f"[Subtasks for: {subject}]\n" + response)
        return jsonify({"subtasks": response})
    except Exception as e:
        return jsonify({"error": f"Failed to generate subtasks: {e}"}), 500



@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(models.get_stats())


if __name__ == '__main__':
    app.run(debug=True)
