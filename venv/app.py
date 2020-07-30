from datetime import datetime
from tqdm import tqdm
import time
import smtplib
from mails import mailing
from bson.json_util import dumps
from flask import Flask, render_template, request, redirect, url_for,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.errors import DuplicateKeyError
from db import get_user, save_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, \
    get_room_members, is_room_admin, update_room, remove_room_members, save_message, get_messages,save_event,get_events,remove_event,remove_all_events,remove_all_members,\
    remove_all_messages,remove_room
import emoji
import sys
reload(sys)
sys.setdefaultencoding('utf8')

app = Flask(__name__)
app.secret_key = "so long"
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


@app.route('/')
def home():
    rooms = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
    return render_template("index.html", rooms=rooms)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ' '
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if user and user.check_password(password_input):
            login_user(user)
            return redirect(url_for('home'))
        else:
            message = 'Failed to login!'
            flash('Login unsucessful.Please check your username and password', 'danger')
    return render_template('login.html', message=message)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ' '
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        mailing(email)
        try:
            save_user(username, email, password)
            flash('Registered successfully. Please login.', 'success')
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User already exists!"
    return render_template('signup.html', message=message)




@app.route('/events/<room_id>/')
@login_required
def event_handle(room_id):
    if is_room_member(room_id,current_user.username):
        return render_template('index1.html',username=current_user.username,room_id=room_id)
    else:
        return  render_template('index.html',username=username)

@app.route('/events/<room_id>/<username>/pg1',methods=['GET','POST'])
def event_handler1(room_id,username):
        return render_template('event.html',room_id=room_id,username=username)


@app.route('/events/<room_id>/<username>/create',methods=['POST','GET'])
@login_required
def event_handler2(room_id, username):
    if request.method == 'POST':
        event = request.form.get('event')
        date1 = request.form.get('date1')
        try:
            save_event(username, room_id, event, date1)
            message = "Successfully added"
            eves = get_events(room_id)
            return render_template('display.html', message=message, username=username,eves=eves)
        except DuplicateKeyError:
            message = "Error"
            return render_template('event.html', message=message)


@app.route('/events/<room_id>/<username>/pg3',methods=['GET','POST'])
def event_handler3(room_id,username):
    eves=get_events(room_id)
    if eves:
            message="Events Available Are"
            return render_template('display.html', message=message,eves=eves)
    else:
            message = "No Events"
            return render_template('display.html', message=message)



@app.route('/events/<room_id>/<username>/pg2',methods=['GET','POST'])
def event_handler5(room_id,username):

    eves=get_events(room_id)
    if eves:
            message="Events Available Are"
            return render_template('delete.html', message=message,eves=eves,room_id=room_id,username=username)
    else:
            message = "NO Events"
            return render_template('delete.html', message=message)




@app.route('/events/<room_id>/<username>/<event>/<created>',methods=['GET','POST'])
@login_required
def event_handler7(event,username,room_id,created):
    remove_event(event,created)
    eves = get_events(room_id)
    message="Events Available are"
    return render_template('display.html', message=message,eves=eves)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    flash('You have logged out successfully', 'success')
    return redirect(url_for('home'))


@app.route('/create-room/', methods=['GET', 'POST'])
@login_required
def create_room():
    message = 'Create your own Rooms'
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]

        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)
            flash('Room created successfully', 'success')
            return redirect(url_for('view_room', room_id=room_id))
        else:
            message = "Failed to create room"
            flash('Failed to create room', 'danger')
    return render_template('create_room.html', message=message)


@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = 'Its very easy to add members'
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            flash('Room edited successfully', 'success')
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message,room_id=room_id)
    else:
        return "<h2>Only room admin can edit the room</h2>", 404


@app.route('/rooms/<room_id>/delete', methods=['GET', 'POST'])
@login_required
def del_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        remove_all_messages(room_id)
        remove_all_members(room_id)
        remove_all_events(room_id)
        remove_room(room_id)
        return redirect(url_for('home'))
    else:
        return "<h2>Only room admin can delete the room</h2>", 404

@app.route('/rooms/<room_id>/del', methods=['GET', 'POST'])
@login_required
def del_msg(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        remove_all_messages(room_id)
        return redirect(url_for('view_room', room_id=room_id))
    else:
        return "<h2>Only room admin can delete the messages</h2>", 404


@app.route('/rooms/<room_id>/')
@login_required
def view_room(room_id):
    room = get_room(room_id)
    a=emoji.emojize(":grinning_face_with_big_eyes:")
    b=emoji.emojize(":winking_face_with_tongue:")
    c=emoji.emojize(":zipper-mouth_face:")
    d=emoji.emojize(":nauseated_face:")
    e=emoji.emojize(":face_with_head-bandage:")
    f=emoji.emojize(":sleepy_face:")
    g=emoji.emojize(":face_with_rolling_eyes:")
    h=emoji.emojize(":lying_face:")
    i=emoji.emojize(":relieved_face:")
    j=emoji.emojize(":pensive_face:")
    k=emoji.emojize(":smirking_face:")
    l=emoji.emojize(":expressionless_face:")
    m=emoji.emojize(":shushing_face:")
    n=emoji.emojize(":thinking_face:")
    o=emoji.emojize(":face_with_raised_eyebrow:")
    p = emoji.emojize(":grinning_face:")
    q = emoji.emojize(":grinning_face_with_smiling_eyes:")
    r = emoji.emojize(":beaming_face_with_smiling_eyes:")
    s = emoji.emojize(":grinning_squinting_face:")
    t = emoji.emojize(":rolling_on_the_floor_laughing:")
    u = emoji.emojize(":grinning_face_with_sweat:")
    v = emoji.emojize(":face_with_tears_of_joy:")
    w = emoji.emojize(":slightly_smiling_face:")
    x = emoji.emojize(":upside-down_face:")
    y = emoji.emojize(":winking_face:")
    a1= emoji.emojize(":smiling_face_with_smiling_eyes:")
    b1= emoji.emojize(":smiling_face_with_halo:")
    c1= emoji.emojize(":face_blowing_a_kiss:")
    d1= emoji.emojize(":smiling_face_with_heart-eyes:")
    e1= emoji.emojize(":star-struck:")
    f1= emoji.emojize(":kissing_face:")
    g1= emoji.emojize(":kissing_face_with_closed_eyes:")
    h1= emoji.emojize(":kissing_face_with_smiling_eyes:")
    i1= emoji.emojize(":face_savoring_food:")
    j1= emoji.emojize(":zany_face:")
    k1= emoji.emojize(":sunglasses:")
    l1= emoji.emojize(":kiss:")
    m1= emoji.emojize(":collision:")
    n1= emoji.emojize(":princess:")
    o1= emoji.emojize(":eyes:")
    q1= emoji.emojize(":pizza:")
    p1= emoji.emojize(":memo:")
    r1= emoji.emojize(":poultry_leg:")
    s1= emoji.emojize(":custard:")
    t1= emoji.emojize(":cookie:")
    u1=emoji.emojize(":sushi:")
    v1=emoji.emojize(":pear:")
    w1=emoji.emojize(":cherries:")
    x1=emoji.emojize(":chocolate_bar:")
    y1=emoji.emojize(":musical_note:")
    a2 = emoji.emojize(":video_game:")
    b2 = emoji.emojize(":family:")
    c2 = emoji.emojize(":hotel:")
    d2 = emoji.emojize(":boy:")
    e2 = emoji.emojize(":girl:")
    f2 = emoji.emojize(":school:")
    g2 = emoji.emojize(":house:")
    h2 = emoji.emojize(":hospital:")
    i2 = emoji.emojize(":bank:")
    j2 = emoji.emojize(":cinema:")
    k2 = emoji.emojize(":station:")
    l2 = emoji.emojize(":ambulance:")
    m2 = emoji.emojize(":airplane:")
    n2 = emoji.emojize(":taxi:")
    o2 = emoji.emojize(":oncoming_automobile:")




    if room and is_room_member(room_id, current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template('view_room.html', username=current_user.username, room_id=room_id, room=room, room_members=room_members,
                                messages=messages,a=a,b=b,c=c,d=d,e=e,f=f,g=g,h=h,i=i,j=j,k=k,l=l,m=m,n=n,o=o,p=p,q=q,r=r,s=s,t=t,u=u,
                               v=v,w=w,x=x,y=y,a1=a1,b1=b1,c1=c1,d1=d1,e1=e1,f1=f1,g1=g1,h1=h1,i1=i1,j1=j1,k1=k1,l1=l1,m1=m1,n1=n1,o1=o1,p1=p1,q1=q1,r1=r1,
                               s1=s1,t1=t1,u1=u1,v1=v1,w1=w1,x1=x1,y1=y1,a2=a2,b2=b2,c2=c2,d2=d2,e2=e2,f2=f2,g2=g2,h2=h2,i2=i2,j2=j2,k2=k2,l2=l2,m2=m2,n2=n2,o2=o2)
    else:
        return "Room not found", 404


@app.route('/rooms/<room_id>/messages/')
@login_required
def get_older_messages(room_id):
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        page = int(request.args.get('page', 0))
        messages = get_messages(room_id, page)
        return dumps(messages)
    else:
        return "Room not found", 404


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room {}: {}".format(data['username'],
                                                                    data['room'],
                                                                    data['message']))
    data['created_at'] = datetime.now().strftime("%d %b, %H:%M")
    save_message(data['room'], data['message'], data['username'])
    socketio.emit('receive_message', data, room=data['room'])


@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data, room=data['room'])


@socketio.on('leave_room')
def handle_leave_room_event(data):
    app.logger.info("{} has left the room {}".format(data['username'], data['room']))
    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data, room=data['room'])


@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == '__main__':
