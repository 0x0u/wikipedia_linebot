import re
import wikipedia
from flask import request, abort
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction)

from src import app, handler, line, languages
from src.wiki import wikipedia_page, wikipedia_search
from src.database import get_user, update_user, get_history, add_history


@app.route('/', methods=['GET'])
def route():
    return 'ok'


@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info('Request body: ' + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    user_id = event.source.user_id
    user_name = line.get_profile(user_id).display_name
    print(f'Received message: \'{message}\' from {user_name}')

    if ':set_lang' in message:
        text = 'Invalid message.'
        if message in [f':set_lang={lang}' for lang in languages.keys()]:
            lang = re.findall(':set_lang=(.+)', message)[0]
            update_user(user_id, lang=lang)
            text = f'Language setting completed -> {languages[lang]}'
        reply_content = TextSendMessage(text=text)

    elif ':set_show_url' in message:
        if message == ':set_show_url=true':
            update_user(user_id, show_url=True)
            text = 'Configured to include URLs in summary messages.'
        elif message == ':set_show_url=false':
            update_user(user_id, show_url=False)
            text = 'Do not add URLs to summary message.'
        else:
            text = 'Invalid message'
        reply_content = TextSendMessage(text=text)

    elif message == ':history':
        history = get_history(user_id)
        text = ''
        items = []
        for h in history:
            item = h.history
            text += f'・{item}\n'
            if len(item) <= 20:
                label = item
            else:
                label = '{:.17}...'.format(item)
            items.append(QuickReplyButton(action=MessageAction(label=label, text=item)))
        quick_reply= QuickReply(items=items) if items else None
        reply_content = TextSendMessage(text=text if text else 'No history yet.', quick_reply=quick_reply)

    else:
        user = get_user(user_id)
        wikipedia.set_lang(user.lang)
        add_history(user_id, message)
        text = wikipedia_page(message, url=user.show_url)
        quick_reply = wikipedia_search(message)
        reply_content = TextSendMessage(text=text, quick_reply=quick_reply)

    line.reply_message(event.reply_token, reply_content)
