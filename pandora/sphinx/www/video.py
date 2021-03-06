import os
import simplejson
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask import current_app as app
from flask_login import login_required, current_user
from flask_wtf import Form
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename

import util.video
from model.video import Video
from model.comment import Comment
from model.user import User
from model.notification import Notification

site = Blueprint('video', __name__)

# @site.route('/play', methods=['GET'])
# def play_video(userid,videoid):
#     page_title='NyanNyan'
#     desc='Blablabla'
#     return render_template('_videoplayer.html',video_data = video)
# 
# @site.route('/uservideos', methods=['GET'])
# def list_uservideos(userid,sort='time'):
#     return render_template('_uservideos.html')

def get_current_videos():
    videos = current_user.videos
    file_display = []
    for video in videos:
        file_saved = util.video.UploadResponse(name=video.title,
                                               size=video.size,
                                               url=url_for('video.play', id=video.id),
                                               delete_url=url_for('video.delete', id=video.id))
        file_display.append(file_saved.get_file())
    return simplejson.dumps({"files": file_display})

@site.route("/manage", methods=['GET'])
@login_required
def manage():
    return render_template('video/manage.html')

@site.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']

        if file:
            filename = secure_filename(file.filename)
            filename = util.video.get_non_conflict_name(filename, current_user)
            mimetype = file.content_type

            if not util.video.allowed_file(filename):
                result = util.video.UploadResponse(name=filename,
                                                   type=mimetype,
                                                   size=0,
                                                   not_allowed_msg="Filetype not allowed")

            else:
                # save then record to db
                video = Video.upload(file, filename, current_user)

                # create thumbnail after saving
                # if mimetype.startswith('image'):
                #     create_thumbnai(filename)

                # return json for js call back
                result = util.video.UploadResponse(name=video.title,
                                                   type=mimetype,
                                                   size=video.size,
                                                   not_allowed_msg=None,
                                                   url=url_for('video.play', id=video.id),
                                                   delete_url=url_for('video.delete', id=video.id))

            # for validation
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        return get_current_videos()

    redirect(url_for('video.manage'))

class CommentForm(Form):
    body = TextAreaField("Any Comments?", validators=[DataRequired()])
    submit = SubmitField("Comment")

@site.route("/play/<id>", methods=['GET', 'POST'])
@login_required
def play(id):
    video = Video.from_id(id)
    comments = video.comments
    if request.method == 'POST':
        try:
            commenttext = request.form['body']
            cmt = Comment.comment(replier_id=current_user.id,
                            content=commenttext,
                            video_id=video.id)
            video.poster.addnewnote(user_from=current_user.id,
                                    type=Notification.TYPE_VIDEOCOMMENT,
                                    video_id=str(video.id)) 
            
            return render_template('video/commentrow.html',comment=cmt)
        except KeyError:
            pass
    video.play_count += 1
    return render_template('video/play.html',
                           video=video,
                           comments=comments)

@site.route("/delete/<id>", methods=['DELETE'])
@login_required
def delete(id):
    video = Video.from_id(id)
    # TODO: better way to check authority (what about admin?)
    if video.poster is not current_user:
        abort(404)
    video.delete()
    return get_current_videos()
    
@site.route("/sharefriendlist",methods=['POST'])
@login_required
def sharefriendlist():
    try:
        user_id = request.form['userid']
    except KeyError:
        abort(400)
    user = User.from_id(user_id)
    return render_template('video/sharefriendlist.html',friendlist = user.getfriends())

@site.route("/doshare",methods=['POST'])
@login_required
def doshare():
    try:
        video_id = request.form['videoid']
        user_id = request.form['userid']
    except KeyError:
        abort(400)
    user = User.from_id(user_id)
    user.addnewnote(user_from = current_user.id,
                    type = Notification.TYPE_VIDEOSHARE,
                    video_id = video_id)
                    
    return 'success'

@site.route("/searchvideo",methods=['GET'])
def searchvideo():
    try:
        keyword = request.args.get('keyword','')
    except KeyError:
        abort(400)
    videolist = Video.search(keyword)
    return render_template('video/videolist.html',videolist=videolist)