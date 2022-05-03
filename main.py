from flask import Flask
from flask import render_template
from flask import url_for
from flask import request
from flask import redirect
from flask import session
from flask import make_response
from flask import abort
from flask import jsonify

from flask_login import LoginManager
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user
from flask_login import login_required

from data import db_session
from data.users import User
from data.books import Book

from forms.user import RegisterForm
from forms.user import LoginForm
from forms.user import ChangePasswordForm 

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MSojJkBfU1VQRVJfU0VDUkVUX0tFWV8jJCUjKCojISYhOTAzMQ=='

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/')
@app.route('/index')
@app.route('/main')
def index():
    db_sess = db_session.create_session()
    books = db_sess.query(Book).all()

    message = ''
    try:
        if request.args['message'] == 'pswd_changed':
            message = 'Пароль успешно сменен'
    except:
        pass

    return render_template('index.html', title='Библиотека', books=books, message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data or User.name == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")

        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.is_authenticated:
        return redirect('/')

    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message='Пароли не совпадают')
                                   
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        
        user = User(
            name=form.name.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('change_password.html', title='Изменение пароля',
                                   form=form,
                                   message='Пароли не совпадают')
                                   
        db_sess = db_session.create_session()
        
        selected_user = db_sess.query(User).filter(User.email == current_user.email).first()
        if not(selected_user.check_password(form.password.data)):
            return render_template('change_password.html', title='Изменение пароля',
                                   form=form,
                                   message='Введен неправильный пароль')
        
        selected_user.set_password(form.new_password.data)
        db_sess.commit()
        return redirect(url_for('index', message='pswd_changed'))
    
    return render_template('change_password.html', title='Регистрация', form=form)


@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if not(current_user.is_admin):
        return abort(403)
    
    if request.method == 'GET':
        return render_template('add_book.html', title='Добавление книги')
    elif request.method == 'POST':
        book = Book(
            title=request.form['name'],
            author=request.form['author'],
            content=request.form['content']
        )
        db_sess = db_session.create_session()
        db_sess.add(book)
        db_sess.commit()
        
        return redirect('/')


@app.route('/delete_book/<id>')
@login_required
def delete_book(id):
    if not(current_user.is_admin):
        return abort(403)

    db_sess = db_session.create_session()

    book = db_sess.query(Book).filter(Book.id == id).first()

    db_sess.delete(book)
    db_sess.commit()

    return redirect('/')
    

@app.route('/edit_book/<id>', methods=['GET', 'POST'])
@login_required
def edit_book(id):
    if not(current_user.is_admin):
        return abort(403)

    db_sess = db_session.create_session()

    book = db_sess.query(Book).filter(Book.id == id).first()

    if request.method == 'GET':
        return render_template('edit_book.html', title='Редактирование книги', book=book)
    elif request.method == 'POST':
        book.title = request.form['name']
        book.author = request.form['author']
        book.content = request.form['content']

        db_sess.commit()

        return redirect('/')


@app.route('/book/<id>')
@login_required
def read_book(id):
    db_sess = db_session.create_session()
    book = db_sess.query(Book).filter(Book.id == id).first()
    
    return render_template('read_book.html', title=book.title, book=book)


@app.route('/search')
def search():
    query = request.args['search'].split()
    
    db_sess = db_session.create_session()

    results = []
    for i in query:
        i = i.lower()
        search_by_title = db_sess.query(Book).filter(Book.title.ilike(f'%{i}%')).all()
        results.extend(search_by_title)
        
        search_by_author = db_sess.query(Book).filter(Book.author.ilike(f'%{i}%')).all()
        results.extend(search_by_author)

        i = i.capitalize()

        search_by_title = db_sess.query(Book).filter(Book.title.ilike(f'%{i}%')).all()
        results.extend(search_by_title)
        
        search_by_author = db_sess.query(Book).filter(Book.author.ilike(f'%{i}%')).all()
        results.extend(search_by_author)

    results = list(set(results))

    return render_template('search.html', books=results)


@app.route('/api/get_books')
def get_books():
    db_sess = db_session.create_session()
    books = db_sess.query(Book).all()

    data = {'books_amount': len(books), 'books': []}
    for book in books:
        book_info = {'title': book.title, 'author': book.author, 'created_date': book.created_date}
        data['books'].append(book_info)

    return jsonify(data)


@app.route('/api/get_book_content/<id>', methods=['POST'])
def get_book_content(id):
    data = dict(request.form)
    print(data)
    db_sess = db_session.create_session()
        
    selected_user = db_sess.query(User).filter(User.email == data['login'] or User.name == data['login']).first()
    if not(selected_user.check_password(data['password'])):
        return abort(403)

    book = db_sess.query(Book).filter(Book.id == id).first()

    return jsonify({'content': book.content})

db_session.global_init("db/db.db")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)