from flask import Flask, render_template, request, redirect, url_for, Response
import mysql.connector
from io import BytesIO
from xhtml2pdf import pisa
import csv

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Add your MySQL password if needed
    database="eventdb"
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/events')
def events():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    cursor.close()
    return render_template('events.html', events=events)

@app.route('/events/new', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        capacity = request.form['capacity']
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, date, location, capacity)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, description, date, location, capacity))
        db.commit()
        cursor.close()
        return redirect(url_for('events'))
    return render_template('event-form.html', event=None)

@app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
def edit_event(id):
    cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        capacity = request.form['capacity']
        cursor.execute("""
            UPDATE events SET title=%s, description=%s, date=%s, location=%s, capacity=%s WHERE id=%s
        """, (title, description, date, location, capacity, id))
        db.commit()
        cursor.close()
        return redirect(url_for('events'))
    cursor.execute("SELECT * FROM events WHERE id = %s", (id,))
    event = cursor.fetchone()
    cursor.close()
    return render_template('event-form.html', event=event)

@app.route('/events/delete/<int:id>')
def delete_event(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM events WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('events'))

@app.route('/events/<int:id>')
def event_detail(id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE id = %s", (id,))
    event = cursor.fetchone()
    cursor.execute("SELECT name, email FROM attendees WHERE event_id = %s", (id,))
    attendees = cursor.fetchall()
    cursor.close()
    return render_template('event_detail.html', event=event, attendees=attendees)

@app.route('/attendees')
def attendees():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT attendees.id, attendees.name, attendees.email, events.title
        FROM attendees
        JOIN events ON attendees.event_id = events.id
    """)
    attendees = cursor.fetchall()
    cursor.close()
    return render_template('attendees.html', attendees=attendees)

@app.route('/attendees/new', methods=['GET', 'POST'])
def add_attendee():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, title FROM events")
    events = cursor.fetchall()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        event_id = request.form['event_id']
        cursor.execute("""
            INSERT INTO attendees (name, email, event_id)
            VALUES (%s, %s, %s)
        """, (name, email, event_id))
        db.commit()
        cursor.close()
        return redirect(url_for('attendees'))
    cursor.close()
    return render_template('attendee-form.html', attendee=None, events=events)

@app.route('/attendees/edit/<int:id>', methods=['GET', 'POST'])
def edit_attendee(id):
    cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        event_id = request.form['event_id']
        cursor.execute("""
            UPDATE attendees SET name=%s, email=%s, event_id=%s WHERE id=%s
        """, (name, email, event_id, id))
        db.commit()
        cursor.close()
        return redirect(url_for('attendees'))
    cursor.execute("SELECT * FROM attendees WHERE id = %s", (id,))
    attendee = cursor.fetchone()
    cursor.execute("SELECT id, title FROM events")
    events = cursor.fetchall()
    cursor.close()
    return render_template('attendee-form.html', attendee=attendee, events=events)

@app.route('/attendees/delete/<int:id>')
def delete_attendee(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM attendees WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('attendees'))

@app.route('/reports')
def reports():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.title, COUNT(a.id) AS tickets_sold, e.capacity, COUNT(a.id)*100 AS revenue
        FROM events e
        LEFT JOIN attendees a ON e.id = a.event_id
        GROUP BY e.id
    """)
    reports = cursor.fetchall()
    cursor.close()
    return render_template('reports.html', reports=reports)

@app.route('/reports/export/csv')
def export_reports_csv():
    cursor = db.cursor()
    cursor.execute("""
        SELECT e.title, COUNT(a.id) AS tickets_sold, e.capacity, COUNT(a.id)*100 AS revenue
        FROM events e
        LEFT JOIN attendees a ON e.id = a.event_id
        GROUP BY e.id
    """)
    rows = cursor.fetchall()
    cursor.close()

    def generate():
        yield 'Event,Tickets Sold,Capacity,Revenue\n'
        for row in rows:
            yield ','.join(str(cell) for cell in row) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=report.csv"})

@app.route('/reports/export/pdf')
def export_reports_pdf():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.title, COUNT(a.id) AS tickets_sold, e.capacity, COUNT(a.id)*100 AS revenue
        FROM events e
        LEFT JOIN attendees a ON e.id = a.event_id
        GROUP BY e.id
    """)
    reports = cursor.fetchall()
    cursor.close()

    html = render_template('reports-pdf.html', reports=reports)
    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf_output = pdf.getvalue()
    return Response(pdf_output, mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=report.pdf"})

if __name__ == '__main__':
    app.run(debug=True)