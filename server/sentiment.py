import json
from urllib.parse import urlparse, urlunparse

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


def service_health_url(service_url):
    parsed = urlparse(service_url)
    if not parsed.scheme or not parsed.netloc:
        return ''
    return urlunparse((parsed.scheme, parsed.netloc, '/health', '', '', ''))


def get_model_status():
    service_url = current_app.config.get('SENTIMENT_SERVICE_URL')
    configured_model = current_app.config.get('MODEL_TYPE') or ''
    if not service_url:
        return {
            'engine': 'local-lexicon',
            'configuredModel': configured_model or 'local-lexicon',
            'modelLoaded': True,
            'mode': 'local',
            'status': 'running',
            'message': '未配置模型服务，当前使用本地词典规则推理'
        }

    health_url = service_health_url(service_url)
    try:
        response = requests.get(health_url, timeout=1.5)
        payload = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        engine = payload.get('engine') or payload.get('configuredModel') or configured_model or 'unknown'
        return {
            'engine': engine,
            'configuredModel': payload.get('configuredModel') or configured_model or engine,
            'modelLoaded': bool(payload.get('modelLoaded')),
            'mode': 'service' if response.ok and payload.get('modelLoaded') else 'fallback',
            'status': 'running' if response.ok and payload.get('modelLoaded') else 'unavailable',
            'device': payload.get('device') or '',
            'serviceUrl': service_url,
            'healthUrl': health_url,
            'message': payload.get('error') or ('模型服务运行中' if response.ok else '模型服务不可用，评论推理将降级为本地词典规则')
        }
    except Exception as exc:
        return {
            'engine': 'local-lexicon',
            'configuredModel': configured_model or 'unknown',
            'modelLoaded': False,
            'mode': 'fallback',
            'status': 'unavailable',
            'serviceUrl': service_url,
            'healthUrl': health_url,
            'message': '模型服务连接失败，评论推理将降级为本地词典规则: {}'.format(exc)
        }


def dump_raw(value):
    return json.dumps(value, ensure_ascii=False)
