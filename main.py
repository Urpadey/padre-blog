from flask import Flask, render_template, redirect, url_for, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
# for wrapping
from functools import wraps
# importing Forms
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os

# ///////////////////////////////////
login_manager = LoginManager()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
email_ = os.environ.get('Email_details')
email_password = os.environ.get('Email_password')

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager.init_app(app)
gravatar = Gravatar(app, size=100, rating='x')


##CONFIGURE TABLES
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship('BlogPost', back_populates='author')
    comments = relationship('Comment', back_populates='comment_author')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship('User', back_populates='posts')
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship('Comment', back_populates='blog')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    comment_author = db.Column(db.String(250), nullable=False)
    comment_author_id = db.Column(db.Integer, ForeignKey('users.id'))
    comment_author = relationship('User', back_populates='comments')
    blog = db.Column(db.String(250), nullable=False)
    blog_id = db.Column(db.Integer, ForeignKey('blog_posts.id'))
    blog = relationship('BlogPost', back_populates='comments')


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# admin_only
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    is_admin = None
    if current_user.is_authenticated:
        if current_user.id == 1:
            is_admin = True
    else:
        is_admin = False

    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, admin=is_admin)


@app.route('/register', methods=['GET', "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        email_invalid = User.query.filter_by(email=email).first()
        if email_invalid:
            error = 'This User Already Exists'
            return render_template('login.html', error=error)
        else:
            new_user = User(
                name=form.name.data,
                email=email,
                password=generate_password_hash(password=form.password.data, method='pbkdf2:sha256', salt_length=16)
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        valid_user = User.query.filter_by(email=email).first()
        if not valid_user:
            error = 'This User does not Exist'
            return render_template("login.html", form=form, error=error)
        if valid_user:
            password_ = form.password.data
            password_checked = check_password_hash(pwhash=valid_user.password, password=password_)
        if not password_checked:
            error = 'This password is wrong, please try again'
            return render_template("login.html", form=form, error=error)
        else:
            login_user(valid_user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    is_admin = None
    if current_user.is_authenticated:
        if current_user.id == 1:
            is_admin = True
    else:
        is_admin = False
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = form.comment.data
            new_comment = Comment(
                text=comment,
                comment_author=current_user,
                blog=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
        else:
            error = 'you need to login to comment'
            return redirect(url_for('login',error=error))
    return render_template("post.html", post=requested_post, admin=is_admin, logged_in=current_user.is_authenticated,
                           form=form)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=['GET', "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=True)


@app.route("/edit-post/<int:post_id>", methods=['GET', "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=True)


@app.route("/delete/<int:post_id>", methods=['GET', "POST"])
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
