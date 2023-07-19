from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import bleach
import smtplib
from dotenv import load_dotenv
import os

load_dotenv()

MY_EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=50,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONNECT TO FLASK-LOGIN
login_manager = LoginManager()
login_manager.init_app(app)



##CONFIGURE TABLES
##CREATE TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the posts property in the User class.
    comment_author = relationship("User", back_populates="comments")

    # Create Foreign Key, "blog_posts.id" the blog_post refers to the tablename of BlogPost.
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the BlogPost object, the "comment" refers to the posts property in the BlogPost class.
    parent_post = relationship("BlogPost", back_populates="comments")

    text = db.Column(db.Text, nullable=False)



# db.create_all()

##CREATE A USER_LOADER CALLBACK DECORATOR
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##CLEAR CKEditor text
def strip_invalid_html(content):
    allowed_tags = ['a', 'abbr', 'acronym', 'address', 'b', 'br', 'div', 'dl', 'dt',
                    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
                    'li', 'ol', 'p', 'pre', 'q', 's', 'small', 'strike',
                    'span', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
                    'thead', 'tr', 'tt', 'u', 'ul']

    allowed_attrs = {
        'a': ['href', 'target', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }

    cleaned = bleach.clean(content,
                           tags=allowed_tags,
                           attributes=allowed_attrs,
                           strip=True)

    return cleaned



@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    form.validate_on_submit()
    if request.method == 'POST':
        email = form.email.data
        found_user_by_email = User.query.filter_by(email=email).first()
        # check if user email already exist in account. if yes, informed user to login
        if found_user_by_email:
            flash(f"The is an account associated with this email: {email}. Please log in")
            return redirect(url_for('login'))

        new_user = User(email=email,
                        password=generate_password_hash(password=form.password.data,
                                                        method="sha256", salt_length=8),
                        name=form.name.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=form)


@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()

    if request.method == 'POST':
        form.validate_on_submit()
        email = form.email.data
        password = form.password.data
        found_user = User.query.filter_by(email=email).first()
        if found_user and check_password_hash(pwhash=found_user.password, password=password):
            login_user(found_user)
            return redirect(url_for('get_all_posts'))
        else:
            flash('Invalid Email or Password')

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        body = strip_invalid_html(form.comment.data)
        new_comment = Comment(text=body,
                              comment_author=current_user,
                              parent_post=requested_post)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        sub = f"Moses's Blog"
        message = f"{request.form.get('message')}\n\nName: {request.form.get('name')}\n" \
                  f"Email: {request.form.get('email')}\n" \
                  f"Phone: {request.form.get('phone')}"

        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()  # create a safe connection
            connection.login(user=MY_EMAIL, password=PASSWORD)
            connection.sendmail(from_addr=MY_EMAIL,
                                to_addrs="moses.mccabe@outlook.com",
                                msg=f"Subject:{sub}, Website Contact Page\n\n{message}")

        flash('Thank you for contacting us; we will respond within three business days.')

    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        body = strip_invalid_html(form.body.data)
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=body,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        body = strip_invalid_html(edit_form.body.data)

        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = body
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
