# main.py
import imaplib
import email
import flask
import random
import string

# 创建Flask对象
app = flask.Flask(__name__)
# 设置session加密，每次启动随机生成32位字母
app.secret_key = random.choices(string.ascii_letters,k=32)

# IMAP类
class Mail:
    # 类初始化函数
    def __init__(self,username,password,server,port,inbox='INBOX'):
        self.username = username
        self.password = password
        self.mailbox = inbox
        self.server = server
        self.port = port
        self.connect()
        self.login()
        self.setbox()
        self.mails = []
        self.lastmail = 0
        self.pull()
    # 连接IMAP服务器
    def connect(self):
        self.conn = imaplib.IMAP4_SSL(self.server,self.port)
    # 登录
    def login(self):
        self.conn.login(self.username,self.password)
        self.status = 1
    # 设置收件箱
    def setbox(self):
        self.conn.select(self.mailbox)
    # 拉取邮件
    def pull(self):
        result,data = self.conn.search(None,"ALL")
        if result!='OK':
            print("或许什么地方出错了")
        for i in data[0].split():
            if int(i)<=self.lastmail:
                continue
            self.lastmail = int(i)
            result,data = self.conn.fetch(i,"(RFC822)")
            if result!='OK':
                ("或许什么地方出错了")
            data = email.message_from_bytes(data[0][1])
            self.mails.append(
                {
                    "id": int(i),
                    "sender": data["From"],
                    "receiver": data["To"],
                    "subject": data["Subject"],
                    "time": data["Date"],
                    "content": data.get_payload(decode=True)
                }
            )
    # 断开与SMTP服务器的连接
    def disconnect(self):
        self.conn.close()
        self.conn.logout()
        self.status = 0

IMAP_CONNECTIONS = {}

def uKey():
    if "key" in flask.request.args.keys():
        flask.session["imapkey"] = flask.request.args["key"]
        return 1
    elif "key" in flask.request.form.keys():
        flask.session["imapkey"] = flask.request.form["key"]
        return 1
    return 0

# 路由/login路径，接收POST请求
@app.route("/login",methods=['POST'])
def login():
    # 临时变量，存储用户请求带有的信息，如果不存在返回None
    username = flask.request.form.get("username")
    password = flask.request.form.get("password")
    IMAPServer = flask.request.form.get("server","imap.feishu.cn")
    IMAPPort = int(flask.request.form.get("port","993"))
    # 如果username或password中有任意为空(None)，跳出并返回错误。
    if not username or not password:
        flask.session["errMsg"] = "未设置凭据"
        return flask.redirect("/login")
    # 否则登入服务器
    flask.session["imapkey"] = ''.join(random.choices(string.ascii_letters,k=16))
    IMAP_CONNECTIONS[flask.session["imapkey"]] = Mail(username,password,IMAPServer,IMAPPort)
    return flask.redirect("/mailbox")

# 路由/login，接受GET请求，返回HTML页面。
@app.route("/login",methods=['GET'])
def loginUI():
    if uKey() or (("imapkey" in flask.session.keys()) and (flask.session.get("imapkey","0") in IMAP_CONNECTIONS.keys())): return flask.redirect("/mailbox")
    return flask.render_template("loginPage.html",err=flask.session.get("errorMsg"))

# 路由/mailbox，接收GET请求，返回HTML页面。
@app.route("/mailbox",methods=['GET'])
def mailbox():
    uKey()
    srv  = flask.session.get("imapkey")
    if not srv: return flask.redirect("/login")
    imap = IMAP_CONNECTIONS.get(srv)
    if not imap: return flask.redirect("/login")
    return flask.render_template("mailList.html",mails=imap.mails)

# 路由/mail/{id}，接收GET请求，返回HTML页面
@app.route("/mail/<id>",methods=['GET'])
def mail(id):
    uKey()
    srv  = flask.session.get("imapkey")
    if not srv: return flask.redirect("/login")
    imap = IMAP_CONNECTIONS.get(srv)
    if not imap: return flask.redirect("/login")
    mail = {"subject":"","content":""}
    for i in imap.mails:
        if i["id"]==int(id):
            mail=i
            break
    return "<h1>%s</h1><div>%s</div>"%(mail["subject"],mail["content"])

# 刷新邮件列表
@app.route("/pullemails",methods=['GET'])
def pullEmails():
    uKey()
    srv  = flask.session.get("imapkey")
    if not srv: return flask.redirect("/login")
    imap = IMAP_CONNECTIONS.get(srv)
    if not imap: return flask.redirect("/login")
    imap.pull()
    return flask.redirect("/mailbox")

# 登出
@app.route("/logout",methods=['GET'])
def logout():
    uKey()
    srv = flask.session.get("imapkey")
    if srv:
        imap = IMAP_CONNECTIONS.get(srv)
        if imap:
            imap.disconnect()
            del imap
    return flask.redirect("/login")

@app.route("/getKey",methods=['GET','POST'])
def getKey():
    uKey()
    if flask.request.method=='GET':
        return flask.render_template("getkey.html")
    elif flask.request.method=='POST':
        return flask.session.get("imapkey","未登录")
    return "401 Unauthorized.",401

@app.route("/",methods=['GET'])
def root():
    return flask.redirect("/mailbox")

@app.route("/useKey",methods=["GET",'POST'])
def useKey():
    if flask.request.method=="POST":
        uKey()
        return flask.redirect("/mailbox")
    elif flask.request.method=='GET':
        return flask.render_template("/useKey.html")
    return "401 Unauthorized.",401

if __name__ == "__main__":
    app.debug = True
    app.run("127.0.0.1",7788)
    
