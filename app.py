from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_paginate import Pagination, get_page_args
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, BooleanField, SelectField, PasswordField  # Добавлен импорт PasswordField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///terminals.db' 
db = SQLAlchemy(app)

# Модели

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Terminal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    active = db.Column(db.Boolean, default=True)
    last_request = db.Column(db.DateTime, default=datetime.utcnow) 

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    terminal_id = db.Column(db.Integer, db.ForeignKey('terminal.id'), nullable=False)
    account_number = db.Column(db.String(20), nullable=False)
    login = db.Column(db.String(80), nullable=False)
    fm = db.Column(db.String(80), nullable=False)
    method = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    time =  db.Column(db.DateTime, default=datetime.utcnow) 
    terminal = db.relationship('Terminal', backref=db.backref('payments', lazy=True))

class BanknoteCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    terminal_id = db.Column(db.Integer, db.ForeignKey('terminal.id'), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, default=0)
    terminal = db.relationship('Terminal', backref=db.backref('banknote_counts', lazy=True))

class IncasationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    terminal_id = db.Column(db.Integer, db.ForeignKey('terminal.id'), nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)
    time =  db.Column(db.DateTime, default=datetime.utcnow) 
    terminal = db.relationship('Terminal', backref=db.backref('incasation_histories', lazy=True))

# Формы

class AddTerminalForm(FlaskForm):
    name = StringField('Название терминала', validators=[DataRequired()])
    address = StringField('Адрес терминала', validators=[DataRequired()])
    ip = StringField('IP адрес', validators=[DataRequired()])
    active = BooleanField('Активен')
    submit = SubmitField('Добавить')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


# Маршруты

@app.route('/payment/<string:z>/<string:m>/<string:id>')
def payment(z, m, id):
        terminal_id = id  # Замените на нужный ID терминала
        fm = 'ФМ'  # Замените на нужное значение
        method = 'ЮГ'  # Замените на нужное значение
        time = datetime.now(pytz.timezone('Europe/Moscow'))  # Используем Московское время

        payment = Payment(
            terminal_id=terminal_id,
            account_number=z,
            login='',  # Поле "login"  убираем, т.к. его нет в запросе
            fm=fm,
            method=method,
            amount=float(m),
            time=time
        )
        db.session.add(payment)
        db.session.commit()
        return 'OK'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session and not session['logged_in']:  # Изменил условие для перехода в форму регистрации
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Вы успешно зарегистрировались! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', title='Регистрация', form=form)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            session['logged_in'] = True
            session['username'] = user.username
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('main'))
        else:
            flash('Неверные имя пользователя или пароль.', 'danger')
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/main')
def main():
    if 'logged_in' in session and session['logged_in']:
        terminals = Terminal.query.all()
        current_datetime = datetime.now()
        return render_template('main.html', title='Главная', logout=logout, terminals=terminals, datetime=current_datetime, terminal=terminal)
    else:
        return redirect(url_for('login'))
@app.route('/add_terminal', methods=['GET', 'POST'])
def add_terminal():
    if 'logged_in' in session and session['logged_in']:
        form = AddTerminalForm()
        if form.validate_on_submit():
            terminal = Terminal(name=form.name.data, address=form.address.data, ip=form.ip.data, active=form.active.data)
            db.session.add(terminal)
            db.session.commit()
            flash('Терминал добавлен!', 'success')
            return redirect(url_for('main'))
        return render_template('add_terminal.html', title='Добавить терминал', form=form)
    else:
        return redirect(url_for('login'))

@app.route('/terminal/<int:terminal_id>')
def terminal(terminal_id):
    if 'logged_in' in session and session['logged_in']:
        terminal = Terminal.query.get_or_404(terminal_id)
        payments = Payment.query.filter_by(terminal_id=terminal_id).order_by(Payment.time.desc()).all()
        banknote_counts = BanknoteCount.query.filter_by(terminal_id=terminal_id).all()
        total_amount = sum(banknote_count.count * banknote_count.nominal for banknote_count in banknote_counts)
        total_count = sum(banknote_count.count for banknote_count in banknote_counts)
        incasation_histories = IncasationHistory.query.filter_by(terminal_id=terminal_id).order_by(IncasationHistory.time.desc()).all()
        current_datetime = datetime.now()
        return render_template('terminal.html', title='Терминал', terminal=terminal,  banknote_counts=banknote_counts, total_amount=total_amount, total_count=total_count, payments=payments, incasation_histories=incasation_histories)
    else:
        return redirect(url_for('login'))

@app.route('/count_<int:nominal>', methods=['GET'])
def count_nominal(nominal):
        terminal_id = request.args.get('terminal_id')

        # Сопоставление номиналов
        nominals_mapping = {
            10: 10,
            5000: 5000,
            50: 50,
            100: 100,
            500: 500,
            1000: 1000
        }

        if nominal in nominals_mapping:
            banknote_count = BanknoteCount.query.filter_by(terminal_id=terminal_id, nominal=nominals_mapping[nominal]).first()
            if banknote_count:
                banknote_count.count += 1
                db.session.commit()
            else:
                banknote_count = BanknoteCount(terminal_id=terminal_id, nominal=nominals_mapping[nominal], count=1)
                db.session.add(banknote_count)
                db.session.commit()

            # Обновление времени последнего запроса терминала
            terminal = Terminal.query.filter_by(id=terminal_id).first()
            if terminal:  # Проверка, найден ли терминал
                terminal.last_request = datetime.utcnow()
                db.session.commit()
            else:
                return 'Terminal not found', 404  # Возвращаем ошибку 404, если терминал не найден

            return 'OK'
        else:
            return 'Invalid nominal', 400

@app.route('/incasation_<int:terminal_id>', methods=['POST'])
def incasation(terminal_id):
    if 'logged_in' in session and session['logged_in']:
        banknote_counts = BanknoteCount.query.filter_by(terminal_id=terminal_id).all()

        if not banknote_counts:
            return 'Нет купюр для инкассации', 400

        total_amount = 0
        total_count = 0
        for banknote_count in banknote_counts:
            total_amount += banknote_count.count * banknote_count.nominal
            total_count += banknote_count.count

        # Сохраняем историю инкассации
        incasation_history = IncasationHistory(
            terminal_id=terminal_id,
            total_amount=total_amount,
            total_count=total_count,
            time=datetime.now(pytz.timezone('Europe/Moscow'))
        )
        db.session.add(incasation_history)

        # Обнуляем счетчик купюр
        for banknote_count in banknote_counts:
            banknote_count.count = 0
            db.session.commit()

        flash(f'Инкассация завершена. Сумма: {total_amount}, Количество купюр: {total_count}')
        return redirect(url_for('terminal', terminal_id=terminal_id))   
    else:
        return 'Unauthorized', 401

@app.route('/incasation_history_<int:terminal_id>')
def incasation_history(terminal_id):
    if 'logged_in' in session and session['logged_in']:
        incasation_histories = IncasationHistory.query.filter_by(terminal_id=terminal_id).order_by(IncasationHistory.time.desc()).all()
        return render_template('incasation_history.html', title='История инкассаций', incasation_histories=incasation_histories)
    else:
        return redirect(url_for('login'))


@app.route('/update_status/<int:terminal_id>')
def update_status(terminal_id):
        terminal = Terminal.query.get_or_404(terminal_id)
        
        # Получаем текущее время по МСК
        msk_timezone = pytz.timezone('Europe/Moscow')
        now_msk = datetime.now(msk_timezone)
        
        # Сохраняем время по МСК в UTC для базы данных
        terminal.last_request = now_msk.astimezone(pytz.utc) 

        db.session.commit()
        return 'OK'

@app.route('/status_<int:terminal_id>')
def status(terminal_id):
    if 'logged_in' in session and session['logged_in']:
        terminal = Terminal.query.get_or_404(terminal_id)
        last_request_utc = terminal.last_request

        # Преобразуем время последнего запроса в Московское время
        last_request_msk = last_request_utc.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Moscow'))

        # Проверяем, прошло ли более 10 секунд с момента последнего запроса
        if datetime.now(pytz.timezone('Europe/Moscow')) - last_request_msk > timedelta(seconds=10):
            return 'Offline'
        else:
            return 'Online'
    else:
        return 'Unauthorized', 401

def get_paginated_items(items, page, per_page):
    start = (page - 1) * per_page
    return items[start:start + per_page]

@app.route('/payments/<terminal_id>')
def payments(terminal_id):
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    payments = Payment.query.filter_by(terminal_id=terminal_id).order_by(Payment.id.desc()).all()  # Фильтруем по терминалу
    total = len(payments)
    payments = get_paginated_items(payments, page, 15)  # Ограничение на 15 записей на странице

    pagination = Pagination(page=page, per_page=15, total=total, css_framework='bootstrap4')

    return render_template('payments.html', payments=payments, terminal_id=terminal_id, page=page, pagination=pagination, terminal=terminal)

@app.route('/incasations/<terminal_id>')
def incasations(terminal_id):
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    incasations = IncasationHistory.query.filter_by(terminal_id=terminal_id).order_by(IncasationHistory.id.desc()).all()  # Фильтруем по терминалу
    total = len(incasations)
    incasations = get_paginated_items(incasations, page, 15)  # Ограничение на 15 записей на странице

    pagination = Pagination(page=page, per_page=15, total=total, css_framework='bootstrap4')

    return render_template('incasations.html', incasations=incasations, terminal_id=terminal_id, page=page, pagination=pagination)




with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)