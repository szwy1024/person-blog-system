import json

import requests
from flask import current_app


POSITIVE_WORDS = {
    '好', '喜欢', '优秀', '精彩', '赞', '开心', '舒服', '漂亮', '强', '棒',
    '满意', '成功', '惊喜', '推荐', '热爱', '顺利', '清晰', '高效'
}

NEGATIVE_WORDS = {
    '差', '讨厌', '垃圾', '失望', '难受', '糟糕', '失败', '生气', '烦',
    '崩溃', '慢', '丑', '坑', '烂', '不行', '问题', '错误', '离谱'
}

NEGATIONS = {'不', '没', '无', '别', '并非', '不是'}


def local_predict(text):
    positive = 0
    negative = 0
    for word in POSITIVE_WORDS:
        if word in text:
            positive += 1
    for word in NEGATIVE_WORDS:
        if word in text:
            negative += 1

    for negation in NEGATIONS:
        if negation in text:
            positive, negative = negative, positive
            break

    total = positive + negative
    if total == 0:
        probabilities = {'positive': 0.22, 'neutral': 0.58, 'negative': 0.20}
        label = 'neutral'
    else:
        pos = 0.18 + 0.72 * positive / total
        neg = 0.18 + 0.72 * negative / total
        neu = max(0.08, 1 - pos - neg)
        norm = pos + neu + neg
        probabilities = {
            'positive': pos / norm,
            'neutral': neu / norm,
            'negative': neg / norm
        }
        label = max(probabilities, key=probabilities.get)

    return {
        'label': label,
        'score': probabilities[label],
        'probabilities': probabilities,
        'raw': {'engine': 'local-lexicon'}
    }


def predict_sentiment(text):
    service_url = current_app.config.get('SENTIMENT_SERVICE_URL')
    if service_url:
        try:
            response = requests.post(service_url, json={'text': text}, timeout=2)
            response.raise_for_status()
            payload = response.json()
            return {
                'label': payload.get('label', 'neutral'),
                'score': float(payload.get('score', payload.get('confidence', 0))),
                'probabilities': payload.get('probabilities', {}),
                'raw': payload
            }
        except Exception as exc:
            fallback = local_predict(text)
            fallback['raw'] = {'engine': 'local-lexicon', 'fallbackReason': str(exc)}
            return fallback
    return local_predict(text)


def dump_raw(value):
    return json.dumps(value, ensure_ascii=False)
