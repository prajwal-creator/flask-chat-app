import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def mailing(receiver):
    sender='chitchat.familia@gmail.com'
    password='chitchat@1'
    message=MIMEMultipart()
    message['From']=sender
    message['To']=receiver
    message['Subject']='CONFIRMATION E-MAIL'
    text='WELCOME TO CHITCHAT FAMILY, HOPE YOU HAVE A GREAT EXPERIENCE'
    part1=MIMEText(text,'plain')
    message.attach(part1)

    try:
       smtpobj=smtplib.SMTP('smtp.gmail.com:587')
       smtpobj.starttls()
       smtpobj.login(sender,password)
       smtpobj.sendmail(sender,receiver,message.as_string())
       print("success")
    except Exception:
       print("error")