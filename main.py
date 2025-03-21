from emmett import App
from emmett import session, now
from emmett.orm import Model, Field, belongs_to, has_many
from emmett.tools.auth import AuthUser
from emmett.orm import Database
from emmett.tools import Auth
from emmett.sessions import SessionManager
from emmett import abort
from emmett import redirect, url
from emmett.tools import requires



app = App(__name__)

class User(AuthUser):
    # will create "users" table and groups/permissions ones
    has_many('posts', 'comments')


class Post(Model):
    belongs_to('user')
    has_many('comments')

    title = Field()
    text = Field.text()
    date = Field.datetime()

    default_values = {
        'user': lambda: session.auth.user.id,
        'date': now
    }
    validation = {
        'title': {'presence': True},
        'text': {'presence': True}
    }
    fields_rw = {
        'user': False,
        'date': False
    }


class Comment(Model):
    belongs_to('user', 'post')

    text = Field.text()
    date = Field.datetime()

    default_values = {
        'user': lambda: session.auth.user.id,
        'date': now
    }
    validation = {
        'text': {'presence': True}
    }
    fields_rw = {
        'user': False,
        'post': False,
        'date': False
    }
    
    
app.config.auth.single_template = True
app.config.auth.registration_verification = False
app.config.auth.hmac_key = "november.5.1955"

db = Database(app)
auth = Auth(app, db, user_model=User)
db.define_models(Post, Comment)


@app.command('setup')
def setup():
    with db.connection():
        # create the user
        user = User.create(
            email="demo@blog.com",
            first_name="bloggy",
            last_name="bloggy",
            password="bloggy"
        )
        # create an admin group
        admins = auth.create_group("admin")
        # add user to admins group
        auth.add_membership(admins, user.id)
        db.commit()
        


app.pipeline = [
    SessionManager.cookies('GreatScott'),
    db.pipe,
    auth.pipe
]


@app.route("/")
async def index():
    posts = Post.all().select(orderby=~Post.date)
    return dict(posts=posts)


@app.route("/post/<int:pid>")
async def one(pid):
    app.log.info(pid)
    def _validate_comment(form):
        app.log.info(form)
        # manually set post id in comment form
        app.log.info(form.params)
        app.log.info(form.params.post)
        form.params.post = pid
        app.log.info(form.params.post)
    # get post and return 404 if doesn't exist
    post = Post.get(pid)
    if not post:
        abort(404)
    # get comments
    comments = post.comments(orderby=~Comment.date)
    # and create a form for commenting if the user is logged in
    app.log.info(session)
    app.log.info(session.auth)
    if session.auth:
        form = await Comment.form(onvalidation=_validate_comment)
        if form.accepted:
            redirect(url('one', pid))
    return locals()


@app.route("/new")
@requires(lambda: auth.has_membership('admin'), url('index'))
async def new_post():
    form = await Post.form()
    if form.accepted:
        redirect(url('one', form.params.id))
    return {'form': form}


auth_routes = auth.module(__name__)


